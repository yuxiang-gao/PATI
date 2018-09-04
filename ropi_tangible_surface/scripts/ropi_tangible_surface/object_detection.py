#!/usr/bin/env python
from ropi_tangible_surface.common_imports import *

import rospy
import cv2

class ObjectManager:
    def __init__(self, debug = True):
        self.init()
        self.debug = debug


    def init(self):
        self.detections = []
        self.depth_img = None
        self.debug_img = None
        
    def set_debug_img(self, img):
        if img is not None and (len(img.shape) < 3 or img.shape[2] != 3):
            self.debug_img = cv2.cvtColor(
                img.astype(np.uint8)[:, :, np.newaxis], cv2.COLOR_GRAY2BGR)
        elif img is not None:
            self.debug_img = img

    def update(self, cnts, depth_img, debug_img=None):
        self.init()
        output = []
        if self.debug and debug_img is None:
            self.set_debug_img(depth_img)
        if debug_img is not None:
            self.set_debug_img(debug_img)
        self.depth_img = depth_img
        for cnt in cnts:
            detection = ObjectDetection()
            out = detection.update(cnt, self.depth_img, self.debug_img)
            self.detections.append(detection)
            output.append(out)
        return output

class ObjectDetection:
    def __init__(self, debug=True):
        self.clear()
        self.debug = debug

    @staticmethod
    def euclidean_dist(pt1, pt2):
        return np.linalg.norm(np.array(pt1) - np.array(pt2))

    def distance_to_center(self, pt):
        return self.euclidean_dist(pt, self.center_of_mass)

    def set_debug_img(self, img):
        if img is not None and (len(img.shape) < 3 or img.shape[2] != 3):
            self.debug_img = cv2.cvtColor(
                img.astype(np.uint8)[:, :, np.newaxis], cv2.COLOR_GRAY2BGR)
        elif img is not None:
            self.debug_img = img

    def clear(self):
        self.cnt = None
        self.hull = None
        self.moments = None
        self.defects = None
        self.center_of_mass = None
        self.object_height = None
        self.grasp_points = None
        self.depth_img = None
        self.debug_img = None

    def update(self, cnt, depth_img, debug_img=None):
        self.clear()
        if self.debug and debug_img is None:
            self.set_debug_img(depth_img)
        if debug_img is not None:
            self.set_debug_img(debug_img)
        self.depth_img = depth_img
        if cv2.contourArea(cnt) < 100:
            rospy.logdebug_throttle(2, 'Contour area too small.')
            return []
        self.cnt = cnt
        self.hull = cv2.convexHull(cnt, returnPoints=False)
        # calculate moments and center of mass
        self.moments = cv2.moments(cnt)
        if self.moments['m00'] != 0:
            cx = int(self.moments['m10'] / self.moments['m00'])  # cx = M10/M00
            cy = int(self.moments['m01'] / self.moments['m00'])  # cy = M01/M00
            theta = 0.5 * np.arctan2(2 * self.moments['m11'],
                                     self.moments['m20'] - self.moments['m02'])
            theta = theta / np.pi * 180
        self.center_of_mass = (cx, cy)
        if self.debug: 
            cv2.circle(self.debug_img, self.center_of_mass, 2, [100, 0, 255],
                    -1)
        # calculate convexity defects
        # self.defects = cv2.convexityDefects(self.cnt, self.hull)
        # # evaluate defects two by two to get fingertips
        # if self.defects is not None:
        #     for i in range(self.defects.shape[0]):
        #         s, e, f, d = self.defects[i, 0]
        #         start = tuple(cnt[s][0])
        #         end = tuple(cnt[e][0])
        #         far = tuple(cnt[f][0])
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        # print (rect)
        if self.debug: cv2.drawContours(self.debug_img, [box], 0, (0,0,255),2)

        ellipse = cv2.fitEllipse(cnt)

        self.grasp_points = self.get_major_axis(box)
        if self.debug: 
            cv2.ellipse(self.debug_img, ellipse,(0,255,0),2)
            cv2.line(self.debug_img, self.grasp_points[0], self.grasp_points[1], [0, 0, 255], 2)
        
        mask = self.get_mask()
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(self.depth_img, mask = mask)  
        self.object_height = max_val  
        # print(min_val, min_loc, max_val, max_loc)
        return mask

    @staticmethod
    def get_major_axis(rect):
        # (x, y), (MA, ma), angle = ellipse
        # major_axis = min(MA, ma)
        # # MA_x, MA_y = int(0.5 * MA * math.sin(angle)), int(0.5 * MA * math.cos(angle))
        # ma_x, ma_y = int(0.5 * major_axis * math.sin(angle)), int(0.5 * major_axis * math.cos(angle))
        # ma_x_top, ma_y_top = int(x + ma_x), int(y + ma_y)
        # ma_x_bot, ma_y_bot = int(x - ma_x), int(y - ma_y)
        # return (ma_x_top, ma_y_top), (ma_x_bot, ma_y_bot)
        rect = np.asarray(rect)
        return tuple(np.int0((rect[0] + rect[1]) / 2)), tuple(np.int0((rect[2] + rect[3]) / 2))

    def get_mask(self):
        mask = np.zeros(self.depth_img.shape, np.uint8)
        cv2.drawContours(mask, [self.cnt], 0, 255, -1)
        # pixel_points = np.transpose(np.nonzero(mask))
        return mask

    def get_grasp_point(self):
        return self.grasp_points, self.object_height
