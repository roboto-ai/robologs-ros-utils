"""Rosbag Utilities

This module contains functions to extract and handle data from ROS bag files.

"""

import glob
import logging
import os
import shutil
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np
from bagpy import bagreader
from PIL import Image
from rosbags.rosbag1 import Reader
from rosbags.serde import deserialize_cdr, ros1_to_cdr
from tqdm import tqdm

from robologs_ros_utils.sources.ros1 import ros_img_tools
from robologs_ros_utils.utils import file_utils, img_utils


def get_bag_info_from_file(rosbag_path: str) -> dict:
    """
    Retrieve metadata from a specified ROS bag file.

    Args:
        rosbag_path (str): The file path to the rosbag.

    Returns:
        dict: A dictionary containing rosbag metadata such as start time, end time, duration, size, and topics.

    Raises:
        Exception: If the rosbag file does not exist or the file provided is not a valid rosbag.
    """
    if not os.path.exists(rosbag_path):
        raise Exception(f"{rosbag_path} does not exist.")

    if not rosbag_path.endswith(".bag"):
        raise Exception(f"{rosbag_path} is not a rosbag.")

    try:
        bag = bagreader(rosbag_path, tmp=True)
    except Exception as e:
        logging.error(f"Couldn't open rosbag due to error: {e}. Skipping...")
        return dict()

    file_stats = os.stat(rosbag_path)

    summary_dict = {
        "file_name": os.path.split(rosbag_path)[1],
        "start_time": bag.start_time,
        "end_time": bag.end_time,
        "duration": bag.end_time - bag.start_time,
        "file_size_mb": str(file_stats.st_size / (1024 * 1024)),
        "topics": bag.topic_table.to_dict("records"),
    }

    return summary_dict


def get_topic_dict(rosbag_metadata_dict: dict) -> dict:
    """
    Extracts the topic information from the rosbag metadata dictionary.

    Args:
        rosbag_metadata_dict (dict): A dictionary containing rosbag metadata.

    Returns:
        dict: A dictionary where keys are topic names and values are metadata about each topic.
    """
    topic_dict = {}

    for entry in rosbag_metadata_dict.get("topics", []):
        topic_dict[entry["Topics"]] = entry

    return topic_dict


def get_bag_info_from_file_or_folder(input_path: str) -> dict:
    """
    Retrieves metadata from a rosbag file or recursively from rosbag files within a given directory.

    Args:
        input_path (str): The file path to a rosbag or a directory containing one or more rosbag files.

    Returns:
        dict: A dictionary where each key is the absolute path of a rosbag, and the value is its corresponding metadata.

    """
    rosbag_info_dict = {}

    if input_path.endswith(".bag"):
        rosbag_info_dict[os.path.abspath(input_path)] = get_bag_info_from_file(input_path)
    else:
        for root, dirs, files in os.walk(input_path):
            for filename in files:
                if filename.endswith(".bag"):
                    full_path = os.path.join(root, filename)
                    rosbag_info_dict[os.path.abspath(full_path)] = get_bag_info_from_file(full_path)

    return rosbag_info_dict


def create_manifest_entry_dict(msg_timestamp: int, rosbag_timestamp: int, file_path: str, index: int) -> dict:
    """
    Create a dictionary entry for the manifest, containing metadata about the message.

    Args:
        msg_timestamp (int): The timestamp from the message.
        rosbag_timestamp (int): The timestamp from the rosbag.
        file_path (str): The file path of the image or message.
        index (int): The index of the message in the topic.

    Returns:
        dict: A dictionary containing metadata about the message.
    """
    _, img_name = os.path.split(file_path)
    return {
        "msg_timestamp": msg_timestamp,
        "rosbag_timestamp": rosbag_timestamp,
        "path": file_path,
        "msg_index": index,
        "img_name": img_name,
    }


def get_image_topic_types() -> list:
    """
    Retrieve the list of image topic types.

    Returns:
        list: A list of strings representing ROS image topic types.
    """
    return ["sensor_msgs/CompressedImage", "sensor_msgs/Image"]


def get_topic_names_of_type(all_topics: list, filter_topic_types: list) -> list:
    """
    Filter topic names based on the specified topic types.

    Args:
        all_topics (list): A list of dictionaries, each containing information about a topic.
        filter_topic_types (list): A list of strings representing the topic types to filter by.

    Returns:
        list: A list of topic names that match the filtered topic types.
    """
    return [x["Topics"] for x in all_topics if x["Types"] in filter_topic_types]


def get_image_name_from_timestamp(timestamp: int, file_format: str = "jpg") -> str:
    """
    Generate an image file name based on the timestamp.

    Args:
        timestamp (int): The timestamp to be incorporated into the image file name.
        file_format (str): The image file format. Defaults to "jpg".

    Returns:
        str: A string representing the image file name.
    """
    return f"{timestamp}.{file_format}"


def get_image_name_from_index(index: int, file_format: str = "jpg", zero_padding: int = 6) -> str:
    """
    Generate an image file name based on the index.

    Args:
        index (int): The index to be incorporated into the image file name.
        file_format (str): The image file format. Defaults to "jpg".
        zero_padding (int): The number of zeros used to pad the index in the file name. Defaults to 6.

    Returns:
        str: A string representing the image file name.
    """
    return f"{str(index).zfill(zero_padding)}.{file_format}"


def replace_ros_topic_name(topic_name: str, replace_character: str = "_") -> str:
    """
    Replace slashes in a ROS topic name with the specified character.

    Args:
        topic_name (str): The ROS topic name to be modified.
        replace_character (str): The character to replace slashes with. Defaults to "_".

    Returns:
        str: The topic name with slashes replaced by the specified character.
    """
    return topic_name.replace("/", replace_character).lstrip(replace_character)


def get_filter_fraction(
    start_time: Optional[float], end_time: Optional[float], start_rosbag: float, end_rosbag: float
) -> Optional[float]:
    """
    Calculate the fraction of the rosbag duration based on the provided start and end times.

    Args:
        start_time (Optional[float]): The start time in seconds from the beginning of the rosbag.
        end_time (Optional[float]): The end time in seconds until the end of the rosbag.
        start_rosbag (float): The start time of the rosbag in seconds.
        end_rosbag (float): The end time of the rosbag in seconds.

    Returns:
        Optional[float]: The fraction of the rosbag that is covered by the start and end times, if applicable; otherwise, None.
    """
    rosbag_duration = end_rosbag - start_rosbag

    if rosbag_duration <= 0:
        return None

    if start_time is not None and end_time is not None:
        return (end_time - start_time) / rosbag_duration

    if start_time is not None:
        return (end_rosbag - start_time) / rosbag_duration

    if end_time is not None:
        return (end_time - start_rosbag) / rosbag_duration

    return 1.0  # if neither start_time nor end_time is specified, the whole rosbag is considered.

    return None


def check_if_in_time_range(t: float, start_time: Optional[float], end_time: Optional[float]) -> bool:
    """
    Check if a given time is within the specified time range.

    Args:
        t (float): The time to check.
        start_time (Optional[float]): The start of the time range.
        end_time (Optional[float]): The end of the time range.

    Returns:
        bool: True if 't' is in the range specified by 'start_time' and 'end_time', False otherwise.
    """

    if start_time is not None and t < start_time:
        return False

    if end_time is not None and t > end_time:
        return False

    return True  # 't' is in the range if it hasn't failed any of the above conditions.

    return False


def get_name_img_manifest() -> str:
    """
    Get the standard file name for the image manifest file.

    Returns:
        str: The file name of the image manifest.
    """
    return "img_manifest.json"


def get_video_from_image_folder(folder: str, save_imgs: bool = True) -> None:
    """
    Create a video from images located in a specified folder.

    Args:
        folder (str): The directory containing the images.
        save_imgs (bool): If False, the original images are deleted after the video is created. Defaults to True.

    Returns:
        None
    """
    img_manifest = file_utils.read_json(os.path.join(folder, get_name_img_manifest()))
    frame_rate = round(img_manifest["topic"]["Frequency"], 2)
    ros_img_tools.create_video_from_images(input_path=folder, output_path=folder, frame_rate=frame_rate)

    if not save_imgs:
        file_utils.delete_files_of_type(folder, file_format_list=[".jpg"])  # assuming the images are in '.jpg' format

    return


def get_images_from_bag(
    rosbag_path: str,
    output_folder: str,
    file_format: str = "jpg",
    topics: Optional[List[str]] = None,
    create_manifest: bool = True,
    naming: str = "sequential",
    resize: Optional[List[int]] = None,
    sample: Optional[int] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> List[str]:
    """
    Extract images from a ROS bag file, with various filtering and configuration options.

    Args:
        rosbag_path (str): Path to the ROS bag file.
        output_folder (str): Directory where the extracted images will be saved.
        file_format (str): Image format for saved files (default is "jpg").
        topics (Optional[List[str]]): List of ROS topics to extract images from. If None, auto-detects image topics.
        create_manifest (bool): Whether to create a manifest file for the extracted images.
        naming (str): Naming scheme for the saved image files ("sequential", "rosbag_timestamp", or "msg_timestamp").
        resize (Optional[List[int]]): If specified, resizes images to [width, height].
        sample (Optional[int]): If specified, only one out of 'sample' images will be extracted.
        start_time (Optional[float]): Start time for extracting messages from the rosbag (in seconds).
        end_time (Optional[float]): End time for extracting messages from the rosbag (in seconds).

    Returns:
        List[str]: List of paths to directories containing the extracted images, one for each topic.
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
                time_from_start_s = rosbag_time_s - rosbag_metadata_dict["start_time"]
                if not check_if_in_time_range(time_from_start_s, start_time, end_time):
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


def convert_offset_s_to_rosbag_ns(offset_s: int, first_rosbag_time_ns: int) -> int:
    """
    Convert a time offset in seconds to nanoseconds and add it to the timestamp of the first entry in the rosbag.

    Args:
        offset_s (int): Time offset in seconds.
        first_rosbag_time_ns (int): Timestamp of the first entry in the rosbag in nanoseconds.

    Returns:
        int: New timestamp in nanoseconds.
    """
    offset_ns = int(offset_s * 1e9)
    return offset_ns + first_rosbag_time_ns


def is_message_within_time_range(
    time_ns: int, start_time_rosbag_ns: Optional[int] = None, end_time_rosbag_ns: Optional[int] = None
) -> Tuple[bool, bool]:
    """
    Check if a ROS message timestamp falls within a specified time range.

    Args:
        time_ns (int): The message's timestamp in nanoseconds.
        start_time_rosbag_ns (Optional[int]): The start of the time range in nanoseconds.
        end_time_rosbag_ns (Optional[int]): The end of the time range in nanoseconds.

    Returns:
        Tuple[bool, bool]:
            - True if the timestamp is within the range, False otherwise.
            - True if the timestamp exceeds the end_time, False otherwise.
    """

    # Check if the message is before the start of the desired time range
    if start_time_rosbag_ns is not None and time_ns < start_time_rosbag_ns:
        return False, False

    # Check if the message is after the end of the desired time range
    if end_time_rosbag_ns is not None and time_ns > end_time_rosbag_ns:
        return False, True

    return True, False


# def get_clipped_bag_file(
#     input_bag_path: str,
#     output_bag_path: str,
#     topic_list: Optional[List[str]] = None,
#     start_time: Optional[Union[float, int]] = None,
#     end_time: Optional[Union[float, int]] = None,
#     timestamp_type: str = "rosbag_ns",
# ) -> None:
#     """
#     Create a clipped rosbag file from an input bag, filtered by topic and time range.
#
#     Args:
#         input_bag_path (str): Path to the input rosbag file.
#         output_bag_path (str): Path where the new clipped bag should be written.
#         topic_list (Optional[List[str]]): List of string topics to be included in the clipped bag.
#         start_time (Optional[Union[float, int]]): The start time from which to include messages.
#         end_time (Optional[Union[float, int]]): The end time until which to include messages.
#         timestamp_type (str): Type of the provided timestamps, "rosbag_ns" for nanoseconds and
#                               "offset_s" for seconds offset.
#
#     Raises:
#         Exception: If an invalid timestamp_type is provided.
#
#     Returns:
#         None
#     """
#
#     if timestamp_type not in ["rosbag_ns", "offset_s"]:
#         raise Exception(f"Robologs: invalid timestamp_type parameter: {timestamp_type}")
#
#     with Bag(output_bag_path, "w") as outbag:
#         msg_counter = 0
#         first_time_stamp = -1
#         for topic, msg, t in Bag(input_bag_path).read_messages():
#             if first_time_stamp < 0:
#                 first_time_stamp = t.to_nsec()
#                 if timestamp_type == "offset_s":
#                     if start_time:
#                         start_time = convert_offset_s_to_rosbag_ns(
#                             offset_s=start_time, first_rosbag_time_ns=first_time_stamp
#                         )
#
#                     if end_time:
#                         end_time = convert_offset_s_to_rosbag_ns(
#                             offset_s=end_time, first_rosbag_time_ns=first_time_stamp
#                         )
#
#             if topic_list:
#                 if topic not in topic_list:
#                     continue
#
#             in_time_range, past_end_time = is_message_within_time_range(
#                 time_ns=t.to_nsec(), start_time_rosbag_ns=start_time, end_time_rosbag_ns=end_time
#             )
#
#             # stop iterating over rosbag if we're past the user specified end-time
#             if past_end_time:
#                 break
#
#             if not in_time_range:
#                 continue
#
#             msg_counter += 1
#             outbag.write(topic, msg, t)
#
#     return


def get_all_topics(rosbag_list: List[str]) -> List[str]:
    """
    Retrieve all unique topics from a list of rosbag files.

    Args:
        rosbag_list (List[str]): List of rosbag file paths.

    Returns:
        List[str]: List of unique topics across all provided rosbag files.
    """
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
