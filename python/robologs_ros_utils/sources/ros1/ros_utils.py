"""Rosbag utilities

This module contains functions to extract data from rosbags.

"""
import glob
import logging
import os
import shutil
from typing import Optional, Tuple, Union

import click
import cv2
import numpy as np
import pandas as pd
from bagpy import bagreader
from PIL import Image
from rosbag import Bag
from rosbags.rosbag1 import Reader
from rosbags.serde import deserialize_cdr, ros1_to_cdr
from tqdm import tqdm

from robologs_ros_utils.sources.ros1 import ros_img_tools
from robologs_ros_utils.utils import file_utils, img_utils


def get_bag_info_from_file(rosbag_path: str) -> dict:
    """
    Args:
        rosbag_path (str): Input file path rosbag.

    Returns:
        dict: Dictionary with rosbag metadata.

    """

    if not os.path.exists(rosbag_path):
        raise Exception(f"{rosbag_path} does not exist.")

    if not rosbag_path.endswith(".bag"):
        raise Exception(f"{rosbag_path} is not a rosbag.")

    try:
        bag = bagreader(rosbag_path)

    except:
        f"Couldn't open rosbag...skipping"
        return dict()

    file_stats = os.stat(rosbag_path)

    summary_dict = dict()
    summary_dict["start_time"] = bag.start_time
    summary_dict["end_time"] = bag.end_time
    summary_dict["duration"] = bag.end_time - bag.start_time
    summary_dict["file_size_mb"] = file_stats.st_size / (1024 * 1024)
    summary_dict["topics"] = bag.topic_table.to_dict("records")

    return summary_dict


def get_topic_dict(rosbag_metadata_dict: dict) -> dict:
    topic_dict = dict()

    if "topics" in rosbag_metadata_dict:
        for entry in rosbag_metadata_dict["topics"]:
            topic_dict[entry["Topics"]] = entry

    return topic_dict


def get_bag_info_from_file_or_folder(input_path: str) -> dict:
    """
    Args:
        input_path (str): Input file path of a rosbag, or folder with multiple rosbags.

    Returns:
        dict: Dictionary with rosbag metadata for each rosbag. The key of the dictionary is the rosbag file path.

    """

    rosbag_info_dict = dict()

    if input_path.endswith(".bag"):
        rosbag_info_dict[os.path.abspath(input_path)] = get_bag_info_from_file(input_path)
    else:
        for filename in sorted(glob.glob(os.path.join(input_path, "./*.bag"))):
            rosbag_info_dict[os.path.abspath(filename)] = get_bag_info_from_file(filename)

    return rosbag_info_dict


def create_manifest_entry_dict(msg_timestamp: int, rosbag_timestamp: int, file_path: str, index: int) -> dict:
    """
    Args:
        msg_timestamp (int):
        rosbag_timestamp (int):
        file_path (str):
        index (int):

    Returns: dict

    """
    _, img_name = os.path.split(file_path)
    return {
        "msg_timestamp": msg_timestamp,
        "rosbag_timestamp": rosbag_timestamp,
        "path": file_path,
        "msg_index": index,
        "img_name": img_name,
    }


def get_image_topic_types():
    """
    Returns:

    """
    return ["sensor_msgs/CompressedImage", "sensor_msgs/Image"]


def get_topic_names_of_type(all_topics: list, filter_topic_types: list) -> list:
    """
    Args:
        all_topics (list):
        filter_topic_types (list):

    Returns:

    """
    return [x["Topics"] for x in all_topics if x["Types"] in filter_topic_types]


def get_image_name_from_timestamp(timestamp: int, file_format: str = "jpg") -> str:
    """
    Args:
        timestamp (int):
        file_format (str):

    Returns:

    """
    img_name = f"{str(timestamp)}.{file_format}"
    return img_name


def get_image_name_from_index(index: int, file_format: str = "jpg", zero_padding: int = 6) -> str:
    """
    Args:
        index ():
        file_format ():
        zero_padding ():

    Returns:

    """
    img_name = f"{str(index).zfill(zero_padding)}.{file_format}"
    return img_name


def replace_ros_topic_name(topic_name: str, replace_character: str = "_") -> str:
    """
    Args:
        topic_name ():
        replace_character ():

    Returns:

    """
    return topic_name.replace("/", replace_character)[1:]


def get_filter_fraction(start_time: Optional[float], end_time: Optional[float], start_rosbag: float, end_rosbag: float):
    """
    Args:
        start_time (float or None):
        end_time (float or None):
        start_rosbag (float):
        end_rosbag (float):

    Returns:

    """
    rosbag_duration = end_rosbag - start_rosbag

    if rosbag_duration <= 0:
        return

    if start_time and end_time:
        return float((end_time - start_time) / rosbag_duration)

    if start_time and not end_time:
        return float((end_rosbag - start_time) / rosbag_duration)

    if end_time and not start_time:
        return float((end_time - start_rosbag) / rosbag_duration)

    if not end_time and not start_time:
        return 1


def check_if_in_time_range(t: float, start_time: float, end_time: float) -> bool:
    """
    Args:
        t (float):
        start_time (float):
        end_time (float):

    Returns:

    """

    if start_time and end_time:
        if t >= start_time and t <= end_time:
            return True
        else:
            return False

    if not start_time and end_time:
        if t <= end_time:
            return True
        else:
            return False

    if start_time and not end_time:
        if t >= start_time:
            return True
        else:
            return False

    if not start_time and not end_time:
        return True


def get_name_img_manifest():
    """
    Returns:

    """
    return "img_manifest.json"


def get_video_from_image_folder(folder: str, save_imgs: bool = True) -> None:
    """
    Args:
        folder (str):
        delete_imgs (bool):

    Returns:

    """
    img_manifest = file_utils.read_json(os.path.join(folder, get_name_img_manifest()))
    frame_rate = round(img_manifest["topic"]["Frequency"], 2)
    ros_img_tools.create_video_from_images(input_path=folder, output_path=folder, frame_rate=frame_rate)

    if not save_imgs:
        file_utils.delete_files_of_type(folder)

    return


def get_images_from_bag(
    rosbag_path: str,
    output_folder: str,
    file_format: str = "jpg",
    topics: Optional[list] = None,
    create_manifest: bool = True,
    naming: str = "sequential",
    resize: Optional[list] = None,
    sample: Optional[int] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
):
    """
    Args:
        rosbag_path (str):
        output_folder (str):
        file_format (str):
        topics (list):
        create_manifest (bool):
        naming (str):
        resize (list):
        sample (int):
        start_time (float):
        end_time (float):

    Returns: None

    """

    rosbag_metadata_dict = get_bag_info_from_file(rosbag_path=rosbag_path)
    topic_dict = get_topic_dict(rosbag_metadata_dict=rosbag_metadata_dict)
    if not rosbag_metadata_dict:
        return

    if not topics:
        all_topics_dict = rosbag_metadata_dict["topics"]
        img_topic_types = get_image_topic_types()
        topics = get_topic_names_of_type(all_topics=all_topics_dict, filter_topic_types=img_topic_types)
    topic_msg_counter_dict = dict()
    total_number_of_images = 0
    manifest_dict = dict()

    for topic in topics:
        if topic not in topic_dict.keys():
            logging.warning(f"Robologs: {topic} not in ROSBag..skipping.")
            continue

        topic_msg_counter_dict[topic] = 0
        total_number_of_images += topic_dict[topic]["Message Count"]
        manifest_dict[topic] = dict()

    nr_imgs_to_extract = total_number_of_images

    if start_time or end_time:
        filter_duration = get_filter_fraction(
            start_time=start_time,
            end_time=end_time,
            start_rosbag=rosbag_metadata_dict["start_time"],
            end_rosbag=rosbag_metadata_dict["end_time"],
        )
        filter_duration = 0 if filter_duration < 0 else filter_duration

        nr_imgs_to_extract = int(total_number_of_images * filter_duration)

    if sample:
        nr_imgs_to_extract /= sample

    if not topics:
        logging.warning(f"Robologs: no image topics to extract in {rosbag_path}...")

        return
    #
    logging.debug(f"Robologs: extracting images...")
    print(f"Robologs: iterating over {total_number_of_images} images to extract: {nr_imgs_to_extract} images")

    with Reader(rosbag_path) as reader:
        connections = [x for x in reader.connections if x.topic in topics]

        if not connections:
            logging.warning(f"Robologs: none of the selected topics are in the ROSBag.")
            return

        with tqdm(total=total_number_of_images) as pbar:
            for it, (connection, t, rawdata) in enumerate(reader.messages(connections=connections)):
                topic = connection.topic
                msg = deserialize_cdr(ros1_to_cdr(rawdata, connection.msgtype), connection.msgtype)
                rosbag_time_s = t * 1e-9
                if not check_if_in_time_range(rosbag_time_s, start_time, end_time):
                    topic_msg_counter_dict[topic] += 1
                    continue

                if sample and not (topic_msg_counter_dict[topic] % sample) == 0:
                    topic_msg_counter_dict[topic] += 1
                    continue

                topic_name_underscore = replace_ros_topic_name(topic)

                msg_timestamp = int(str(msg.header.stamp.sec) + str(msg.header.stamp.nanosec))

                output_images_folder_folder_path = os.path.join(output_folder, topic_name_underscore)

                if not os.path.exists(output_images_folder_folder_path):
                    os.makedirs(output_images_folder_folder_path)

                if msg.__msgtype__ == "sensor_msgs/msg/Image":
                    img_encodings = {
                        "rgb8": "RGB",
                        "rgba8": "RGBA",
                        "mono8": "L",
                        "8UC3": "RGB",
                        "bgra8": "RGBA",
                        "bgr8": "RGB",
                    }
                    cv_image = np.array(Image.frombytes(img_encodings[msg.encoding], (msg.width, msg.height), msg.data))
                    if msg.encoding == "bgra8":
                        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGRA2RGBA)

                if msg.__msgtype__ == "sensor_msgs/msg/CompressedImage":
                    if "compressedDepth" in msg.format:
                        cv_image = ros_img_tools.convert_compressed_depth_to_cv2(msg)
                    else:
                        cv_image = ros_img_tools.convert_image_to_cv2(msg)

                if naming == "rosbag_timestamp":
                    image_name = get_image_name_from_timestamp(timestamp=t, file_format=file_format)

                elif naming == "msg_timestamp":
                    image_name = get_image_name_from_timestamp(timestamp=msg_timestamp, file_format=file_format)

                else:
                    image_name = get_image_name_from_index(index=topic_msg_counter_dict[topic], file_format=file_format)

                image_name = f"{topic_name_underscore}_{image_name}"

                image_path = os.path.join(output_images_folder_folder_path, image_name)

                if resize:
                    cv_image = img_utils.resize_image(img=cv_image, new_width=resize[0], new_height=resize[1])

                cv2.imwrite(image_path, cv_image)

                if create_manifest:
                    manifest_dict[topic][image_name] = create_manifest_entry_dict(
                        msg_timestamp=msg_timestamp,
                        rosbag_timestamp=t,
                        file_path=image_path,
                        index=topic_msg_counter_dict[topic],
                    )

                if topic in topic_msg_counter_dict.keys():
                    topic_msg_counter_dict[topic] += 1

                pbar.update(1)

        output_imgs_folder_list = list()

        if create_manifest:
            for key in manifest_dict.keys():
                output_images_folder_folder_path = os.path.join(output_folder, replace_ros_topic_name(key))
                output_imgs_folder_list.append(output_images_folder_folder_path)
                if not os.path.exists(output_images_folder_folder_path):
                    os.makedirs(output_images_folder_folder_path)

                output_dict = dict()
                output_dict["images"] = manifest_dict[key]
                output_dict["topic"] = topic_dict[key]

                output_path_manifest_json = os.path.join(output_images_folder_folder_path, get_name_img_manifest())

                # only create manifest file if it doesn't already exist.
                if not os.path.exists(output_path_manifest_json):
                    file_utils.save_json(output_dict, output_path_manifest_json)

    return output_imgs_folder_list


def convert_offset_s_to_rosbag_ns(offset_s: int, first_rosbag_time_ns: int):

    offset_ns = int(offset_s * 1e9)
    return offset_ns + first_rosbag_time_ns


def is_message_within_time_range(
    time_ns: int, start_time_rosbag_ns: Optional[int] = None, end_time_rosbag_ns: Optional[int] = None
) -> Tuple[bool, bool]:
    """
    This function checks if a timestamp is withing a specified timerange and returns True or False if we are. It also
    returns a second boolean to indicate if we are past the end time. This can be used to break out of the loop early.
    Args:
        time_ns (int):
        start_time_rosbag_ns (int):
        end_time_rosbag_ns (int):

    Returns: Turple of booleans

    """

    if start_time_rosbag_ns:
        if time_ns < start_time_rosbag_ns:
            return False, False

    if end_time_rosbag_ns:
        if time_ns > end_time_rosbag_ns:
            return False, True

    return True, False


def get_clipped_bag_file(
    input_bag_path: str,
    output_bag_path: str,
    topic_list: Optional[list] = None,
    start_time: Optional[Union[float, int]] = None,
    end_time: Optional[Union[float, int]] = None,
    timestamp_type: str = "rosbag_ns",
):
    """
    Args:
        input_bag_path ():
        output_bag_path ():
        topic_list ():
        start_time ():
        end_time ():
        timestamp_type ():

    Returns:

    """

    if timestamp_type not in ["rosbag_ns", "offset_s"]:
        raise Exception(f"Robologs: invalid timestamp_type parameter: {timestamp_type}")

    with Bag(output_bag_path, "w") as outbag:
        msg_counter = 0
        first_time_stamp = -1
        for topic, msg, t in Bag(input_bag_path).read_messages():
            if first_time_stamp < 0:
                first_time_stamp = t.to_nsec()
                if timestamp_type == "offset_s":
                    if start_time:
                        start_time = convert_offset_s_to_rosbag_ns(
                            offset_s=start_time, first_rosbag_time_ns=first_time_stamp
                        )

                    if end_time:
                        end_time = convert_offset_s_to_rosbag_ns(
                            offset_s=end_time, first_rosbag_time_ns=first_time_stamp
                        )

            if topic_list:
                if topic not in topic_list:
                    continue

            in_time_range, past_end_time = is_message_within_time_range(
                time_ns=t.to_nsec(), start_time_rosbag_ns=start_time, end_time_rosbag_ns=end_time
            )

            # stop iterating over rosbag if we're past the user specified end-time
            if past_end_time:
                break

            if not in_time_range:
                continue

            msg_counter += 1
            outbag.write(topic, msg, t)

    return


def get_all_topics(rosbag_list):
    topic_list = list()
    for rosbag_file in rosbag_list:
        summary_dict = get_bag_info_from_file(rosbag_file)
        if summary_dict:
            if "topics" in summary_dict.keys():
                topic_dict = get_topic_dict(summary_dict)
                for key in topic_dict.keys():
                    topic_list.append(key)
    return topic_list


def get_csv_data_from_bag(input_dir_or_file: str, output_dir: str, topic_list: list = None) -> None:
    """
    Extract CSV data from rosbag files and move the CSV files to the specified output directory.

    This function can accept either a directory of rosbag files or a single rosbag file.

    Parameters
    ----------
    input_dir_or_file : str
        The directory containing the rosbag files or a path to a single rosbag file.
    output_dir : str
        The directory where the extracted CSV files should be moved.
    topic_list : list, optional
        List of topics to be extracted. If not provided, all topics will be extracted.

    Returns
    -------
    None

    """

    if os.path.isfile(input_dir_or_file):
        rosbag_files = [input_dir_or_file]
    else:
        # List of rosbag files
        rosbag_files = glob.glob(os.path.join(input_dir_or_file, "*.bag"))

    # Loop over each rosbag file
    for rosbag_file in rosbag_files:  # List of rosbag files
        bag = bagreader(rosbag_file)

        # Get all topics
        all_topics = get_all_topics([rosbag_file])

        # If a topic list is specified, filter the topics
        if topic_list is not None:
            all_topics = [topic for topic in all_topics if topic in topic_list]

        # Create subfolder in output directory with rosbag name (without .bag)
        rosbag_name = os.path.basename(rosbag_file).replace(".bag", "")
        rosbag_dir = os.path.join(output_dir, rosbag_name)
        os.makedirs(rosbag_dir, exist_ok=True)

        # Loop over each topic
        for topic in all_topics:
            data = bag.message_by_topic(topic)

            if data:
                # construct the full destination path, including the file name
                destination = os.path.join(rosbag_dir, os.path.basename(data))

                # move the file
                shutil.move(data, destination)

    return