import os

import click

from robologs_ros_utils.sources.ros1 import ros_utils
from robologs_ros_utils.utils import file_utils


def process_topics(ctx, param, value):
    """Callback function to process topics input."""
    if value:
        return [topic.strip() for topic in value.split(",")]
    else:
        return None


@click.command()
@click.option("--input", "-i", type=str, required=True, help="A single rosbag, or directory containing rosbags")
@click.option("--output", "-o", type=str, required=True, help="Output directory for CSV files")
@click.option(
    "--topics", "-t", type=str, default=None, callback=process_topics, help="Comma-separated list of topics to extract"
)
def get_csv_data_from_bag(input, output, topics):
    """
    Extract CSV data from rosbag files and move the CSV files to the specified output directory.
    """

    # Convert topics tuple to list if it's not None
    topic_list = list(topics) if topics else None

    ros_utils.get_csv_data_from_bag(input_dir_or_file=input, output_dir=output, topic_list=topic_list)

    return


if __name__ == "__main__":
    get_csv_data_from_bag()
