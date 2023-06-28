# robologs-ros-utils

## What is robologs-ros-utils

robologs-ros-utils is a collection of utility functions to extract, convert and analyze ROS data. 

## Python Quickstart<a name="python-quickstart" />

Installing robologs-ros-utils is easy using the pip package manager.

We suggest that you use a clean environment to avoid any dependency conflicts:
```bash
pip install robologs-ros-utils
```

From here, you can use robologs-ros-utils in your Python code as follows:

```python
from robologs_ros_utils.sources.ros1 import ros_utils

ros_utils.get_images_from_bag(
         rosbag_path="/path/to/rosbag.bag",
         output_folder="/output_imgs/",
         file_format="jpg",
         create_manifest=True,
         topics="/camera/image_raw",
         naming="sequential",
         resize=[640,480],
         sample=2,
         start_time=0,
         end_time=10)
```
## Command Line Utilities
After you install robologs-ros-utils, you can also use the command line utilities to extract data from rosbag files.

Run the following command to see the available options:
```bash 
robologs-ros-utils --help
```

### Examples

If you want to extract images from the command line:
```bash
robologs-ros-utils get-images --help
```

Or if you want to get metadata from a rosbag file:
```bash
robologs-ros-utils get-summary --help
```

## Use Docker 
You can build a local version of the robologs-ros-utils Docker image as follows:
```bash
./build_image.sh
```

And here is how you can run a robologs-ros-utils command inside the Docker image:
```bash
docker run -v ~/Desktop/scratch/:/input/ -it --rm robologs-ros-utils-image robologs-ros-utils get-videos -i /input/example_bag_small.bag -o /input/ --naming rosbag_timestamp --format jpg --save-images
```

Do you have a request for a data format that's not listed above? Raise an issue or join our Slack community and make a request!

## Community

If you have any questions, comments, or want to chat, please join [our Slack channel](#).

## Contribute 
### How to Contribute

#### How to run tests, mypy, isort and black?

```bash
# activate poetry shell
poetry shell

# install dependencies
poetry update

cd ~/Code/robologs-ros-utils/python/

# run the tests
poetry run coverage run -m --source=robologs_ros_utils pytest tests

# run the coverage report
poetry run coverage report

# run black -> remove the --check to reformat
poetry run black --check .

# run my py
poetry run mypy robologs_ros_utils/sources/

# run isort -> remove the --check to reformat
poetry run isort --check-only .
```

We welcome contributions to robologs-ros-utils. Please see our [contribution guide](#) and our [development guide](#) for details.

### Contributors

<a href="https://github.com/roboto-ai/robologs-ros-utils/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=roboto-ai/robologs-ros-utils" />
</a>

Made with [contrib.rocks](https://contrib.rocks).
