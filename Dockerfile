FROM tiryoh/ros2-desktop-vnc:humble

RUN apt-get update && apt-get install -y \
    ros-humble-turtlebot3 \
    ros-humble-turtlebot3-msgs \
    ros-humble-turtlebot3-simulations \
    ros-humble-navigation2 \
    ros-humble-nav2-bringup \
    ros-humble-robot-localization \
    ros-humble-gazebo-ros-pkgs \
    python3-colcon-common-extensions \
 && rm -rf /var/lib/apt/lists/*

# 지표 플롯용 matplotlib (numpy 2.x 호환 버전으로 업그레이드)
RUN pip install -U matplotlib

# 모든 터미널에서 자동으로 ROS 환경 + 로봇 모델 + 워크스페이스 오버레이가 잡히도록
ENV TURTLEBOT3_MODEL=waffle
RUN echo "source /opt/ros/humble/setup.bash" >> /etc/bash.bashrc && \
    echo "export TURTLEBOT3_MODEL=waffle" >> /etc/bash.bashrc && \
    echo "source /home/ubuntu/ros2_ws/install/setup.bash 2>/dev/null" >> /etc/bash.bashrc