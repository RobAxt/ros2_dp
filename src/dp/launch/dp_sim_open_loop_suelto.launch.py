# Copyright 2025 pgonzal@fi.uba.ar
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable

from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    gazebo_models_path = 'models'
    pkg_share_gazebo = FindPackageShare('dp').find('dp')    
    gazebo_models_path = os.path.join(pkg_share_gazebo, gazebo_models_path)
    
    # Si la variable ya existe, la extendemos; si no, la creamos
    set_env_vars_resources = SetEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        gazebo_models_path
    )
    print(f"GZ_SIM_RESOURCE_PATH set to: {gazebo_models_path}")

    # Launch Arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default=True)

    # Obtener URDF via xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name='xacro')]),
            ' ',
            PathJoinSubstitution(
                [FindPackageShare('dp'),
                 'urdf', 'double_pendulum_suelto.xacro']
            ),
        ]
    )
    
    # En caso de tener el URDF en vez del xacro es más simple pero menos funcional
    #urdf_path = os.path.join(
    #    FindPackageShare('dp').find('dp'),
    #    'urdf', 'double_pendulum.urdf'
    #)

    # Leer el URDF como string
    #with open(urdf_path, 'r') as urdf_file:
    #    robot_description_content = urdf_file.read()

    robot_description = {'robot_description': robot_description_content}
    robot_controllers = PathJoinSubstitution(
        [
            FindPackageShare('dp'),
            'config',
            'ros2_controllers.yaml',
        ]
    )    
    
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )

    gz_spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-topic', 'robot_description',
                    '-name', 'double_pendulum', '-allow_renaming', 'true'
                    '-x', '0',      # Coordenada X
                    '-y', '0',      # Coordenada Y
                    '-z', '1.0'     # Coordenada Z (altura del escritorio)
                    ],
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
    )
     
    # Con un "controlador de esfuerzos" en realidad puedo aplicar directamente torque en los ejes
    # No hay tal cosa como un control de lazo cerrado
    effort_controller_spawner = Node(
    package='controller_manager',
    executable='spawner',
    arguments=[
        'effort_controller',
        '--param-file',
        robot_controllers
        ],
    )

    #joint_trajectory_controller_spawner = Node(
    #    package='controller_manager',
    #    executable='spawner',
    #    arguments=[
    #        'position_controller',
    #        '--param-file',
    #        robot_controllers
    #        ],
    #)

    # Bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )
    
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=['-d', os.path.join(get_package_share_directory('dp'), 'config', 'display.rviz')]
    )
    
    gui_control_node = Node(
        package='dp',
        executable='gui_set_torque.py',
        name='gui_set_torque',
        output='screen',
    )

    return LaunchDescription([
        set_env_vars_resources,
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [PathJoinSubstitution([
                    FindPackageShare('ros_gz_sim'),
                    'launch',
                    'gz_sim.launch.py'
                ])]
            ),
            launch_arguments=[(
                'gz_args',
                ['-r -v 1 ', PathJoinSubstitution([
                    FindPackageShare('dp'),
                    'worlds',
                    'double_pendulum_espacio.world'
                ])]
            )]
        ),        
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=gz_spawn_entity,
                on_exit=[joint_state_broadcaster_spawner],
            )
        ),
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_state_broadcaster_spawner,
                on_exit=[effort_controller_spawner],
            )
        ),
        #RegisterEventHandler(
        #    event_handler=OnProcessExit(
        #        target_action=joint_state_broadcaster_spawner,
        #        on_exit=[joint_trajectory_controller_spawner],
        #    )
        #),
        bridge,
        node_robot_state_publisher,
        gz_spawn_entity,
        rviz_node,
        gui_control_node,
        # Launch Arguments
        DeclareLaunchArgument(
            'use_sim_time',
            default_value=use_sim_time,
            description='If true, use simulated clock'),
    ])    
