# State enum
uint8 CURSOR_PRESSED=0
uint8 CURSOR_DRAGGED=1
uint8 CURSOR_RELEASED=2

string id
uint8 state
float64 elapsed_time
geometry_msgs/Point cursor
geometry_msgs/Point cursor_prev