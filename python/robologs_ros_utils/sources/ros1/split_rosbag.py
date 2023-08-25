import click

from robologs_ros_utils.sources.ros1 import ros_utils


@click.command()
@click.option("--input", "-i", type=str, required=True, help="A single rosbag, or directory containing rosbags")
@click.option("--output", "-o", type=str, required=True, help="Output directory for split rosbags")
@click.option("--chunks", "-c", type=int, required=True, help="Number of chunks to split each rosbag into")
def split_rosbag(input, output, chunks):
    """
    Split rosbag files into smaller chunks and save them to the specified output directory.
    """
    ros_utils.split_rosbag(input_path=input, chunks=chunks, output_folder=output)


if __name__ == "__main__":
    split_rosbag()
