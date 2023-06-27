from inspect import getmembers

import click

from robologs_ros_utils.connectors.commands import connectors
from robologs_ros_utils.sources.ros1.commands import ros


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
        click.echo("Robologs is an open source collection of sensor data transforms")
        click.echo("Run robologs --help to see a list of available commands")
        click.echo("")


cli.add_command(ros)
cli.add_command(connectors)


def main():
    cli()


if __name__ == "__main__":
    main()
