import glob
import os
import subprocess

import cv2
import numpy as np


def convert_compressed_depth_to_cv2(compressed_depth):
    """
    Converts a ROS compressedDepth image into an OpenCV image.

    Args:
        compressed_depth: A sensor_msgs/CompressedImage message from a ROS compressedDepth topic.

    Returns:
        OpenCV image representing the depth image.

    Raises:
        Exception: If the compression type is not 'compressedDepth' or the depth image could not be decoded.

    Note:
        Code adapted from: https://answers.ros.org/question/249775/display-compresseddepth-image-python-cv2/
    """
    depth_fmt, compr_type = compressed_depth.format.split(";")
    depth_fmt = depth_fmt.strip()
    compr_type = compr_type.strip().replace(" png", "")

    if compr_type != "compressedDepth":
        raise Exception("Compression type is not 'compressedDepth'. Incorrect topic subscribed.")

    depth_header_size = 12
    raw_data = compressed_depth.data[depth_header_size:]

    depth_img_raw = cv2.imdecode(np.frombuffer(raw_data, np.uint8), cv2.IMREAD_UNCHANGED)

    if depth_img_raw is None:
        raise Exception("Could not decode compressed depth image. Adjust 'depth_header_size' if necessary.")

    depth_img_norm = cv2.normalize(depth_img_raw, depth_img_raw, 0, 255, norm_type=cv2.NORM_MINMAX)
    depth_img_colormap = cv2.applyColorMap(depth_img_raw, cv2.COLORMAP_JET)

    return depth_img_colormap


def convert_image_to_cv2(msg):
    """
    Converts a ROS image message into an OpenCV image.

    Args:
        msg: A sensor_msgs/Image message.

    Returns:
        OpenCV image.
    """
    np_arr = np.frombuffer(msg.data, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)


def create_video_from_images(input_path, output_path, output_name="video.mp4", frame_rate=12, resize=None):
    """
    Creates a video from a collection of images stored in a specified directory.

    Args:
        input_path (str): Directory where the input images are stored.
        output_path (str): Directory where the output video will be saved.
        output_name (str): Name of the output video file. Defaults to 'video.mp4'.
        frame_rate (int): Frame rate of the output video. Defaults to 12.
        resize (float, optional): Factor by which to resize the images. If None, images are not resized.

    Returns:
        None
    """
    img_array = []
    output_video_path = os.path.join(output_path, output_name)
    output_video_path_temp = os.path.join(output_path, "temp.mp4")

    img_list = sorted(glob.glob(os.path.join(input_path, "./*.jpg")))

    if not img_list:
        img_list = sorted(glob.glob(os.path.join(input_path, "./*.png")))

    if not img_list:
        print("No images found in the specified directory.")
        return

    for filename in img_list:
        img = cv2.imread(filename)
        if resize:
            img = cv2.resize(img, (0, 0), fx=resize, fy=resize, interpolation=cv2.INTER_LANCZOS4)

        height, width = (img.shape[0], img.shape[1]) if len(img.shape) == 3 else img.shape
        size = (width, height)
        img_array.append(img)

    out = cv2.VideoWriter(output_video_path_temp, cv2.VideoWriter_fourcc(*"mp4v"), frame_rate, size)

    for i in range(len(img_array)):
        out.write(img_array[i])
    out.release()

    # Using FFmpeg to convert the temporary video to final format
    subprocess.call(["ffmpeg", "-i", output_video_path_temp, "-vcodec", "libx264", "-y", output_video_path])
    os.remove(output_video_path_temp)
