from inspect import getmembers

import click

from robologs_ros_utils.sources.ros1 import (
    clip_rosbag,
    get_csv_data_from_bag,
    get_images_from_bag,
    get_summary_from_bag,
    get_videos_from_bag,
)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        click.echo(
            """
               __          __                
   _________  / /_  ____  / /___  ____ ______
  / ___/ __ \/ __ \/ __ \/ / __ \/ __ `/ ___/
 / /  / /_/ / /_/ / /_/ / / /_/ / /_/ (__  ) 
/_/   \____/_.___/\____/_/\____/\__, /____/  
                               /____/        
"""
        )
    if ctx.invoked_subcommand is None:
        click.echo("Robologs is an open source collection of ROS-related tools")
        click.echo("Run robologs-ros-utils --help to see a list of available commands")
        click.echo("")


cli.add_command(get_images_from_bag.get_images)
cli.add_command(get_videos_from_bag.get_videos)
cli.add_command(get_summary_from_bag.get_summary)
cli.add_command(clip_rosbag.clip_rosbag)
cli.add_command(get_csv_data_from_bag.get_csv_data_from_bag)


def main():
    cli()


if __name__ == "__main__":
    main()
