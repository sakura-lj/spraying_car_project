#!/usr/bin/env python3

import rospy


def main():
    rospy.init_node("waypoint_follower")
    waypoints_file = rospy.get_param("~waypoints_file", "")
    rospy.logwarn("waypoint_follower placeholder started; no move_base goals are sent.")
    rospy.loginfo("Reserved waypoints file: %s", waypoints_file)
    rospy.spin()


if __name__ == "__main__":
    main()
