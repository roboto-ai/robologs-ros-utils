import os.path
import json

import click

from robologs_ros_utils.sources.ros1 import ros_utils
from robologs_ros_utils.utils import file_utils


@click.command()
@click.option("--input", "-i", type=str, required=True, help="A single rosbag, or folder with rosbags")
@click.option("--output", "-o", type=str, required=True, help="Output directory, or json path")
@click.option("--file-name", "-f", type=str, default="rosbag_metadata.json", help="Output file name")
@click.option("--split", "-s", is_flag=True, help="Save individual metadata files next to each rosbag")
def get_summary(input, output, file_name, split):
    """Get summary of Rosbag1 data"""

    input_path = input
    output_path = output
    output_filename = file_name

    rosbag_info_dict = ros_utils.get_bag_info_from_file_or_folder(input_path=input_path)

    if split:
        for bag_path, bag_info in rosbag_info_dict.items():
            bag_dir = os.path.dirname(bag_path)
            bag_name = "." + os.path.basename(bag_path).replace(".bag", ".json")
            output_file_path = os.path.join(bag_dir, bag_name)
            file_utils.save_json(data=bag_info, path=output_file_path)
    else:
        if os.path.isdir(output_path):
            output_file_path = os.path.join(output_path, output_filename)
        elif os.path.isfile(output_path):
            output_file_path = output_path
        else:
            raise ValueError("Invalid output path provided.")

        file_utils.save_json(data=rosbag_info_dict, path=output_file_path)

    return


if __name__ == "__main__":
    get_summary()

