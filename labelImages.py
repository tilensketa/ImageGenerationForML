import cv2
import os
from multiprocessing import Pool
import argparse

def process_image(image_path, dest_folder, num_objects):
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error loading the image: {image_path}")
        return
    height, width, channels = image.shape

    left_list = []
    right_list = []
    top_list = []
    bottom_list = []

    objects_found = []
    delta_red = 255 / num_objects

    for object_index in range(num_objects):
        object_red_channel = (object_index + 1) * delta_red
        top, bottom, left, right = height, 0, width, 0
        found = False

        for y in range(0, height, 2):
            for x in range(0, width, 2):
                b, g, r = image[y, x]
                if object_red_channel - 1 <= r <= object_red_channel + 1:
                    found = True
                    top = min(top, y)
                    bottom = max(bottom, y)
                    left = min(left, x)
                    right = max(right, x)

        if found:
            objects_found.append(object_index)
        left_list.append(left)
        right_list.append(right)
        top_list.append(top)
        bottom_list.append(bottom)
    
    objects_info = [
        {
            "index": i,
            "xmin": left_list[i],
            "xmax": right_list[i],
            "ymin": top_list[i],
            "ymax": bottom_list[i],
        }
        for i in objects_found
    ]
    create_annotation_txt(image_path, dest_folder, width, height, objects_info)

def process_image_wrapper(args):
    return process_image(*args)

def create_annotation_txt(image_path, dest_folder, image_width, image_height, objects):
    image_folder, image_filename = os.path.split(image_path)
    label_filename = os.path.splitext(image_filename)[0] + ".txt"
    label_path = os.path.join(dest_folder, label_filename)

    with open(label_path, "w") as file:
        data = ""
        for obj in objects:
            left = obj["xmin"]
            right = obj["xmax"]
            top = obj["ymin"]
            bottom = obj["ymax"]
            index = obj["index"]

            centerX = (right + left) / 2
            centerY = (top + bottom) / 2
            relCenterX = centerX / image_width
            relCenterY = centerY / image_height

            width = right - left
            height = bottom - top
            relWidth = width / image_width
            relHeight = height / image_height

            data += f"{index} {relCenterX} {relCenterY} {relWidth} {relHeight} \n"
        file.write(data)

def read_classes_from_file(file_path):
    with open(file_path, 'r') as file:
        classes = [line.strip() for line in file.readlines()]
    return classes

def process_images_parallel_in_folder(args, num_processes=10):
    folder_path = args.source
    label_path = args.dest
    classes_path = args.classes
    classes = read_classes_from_file(classes_path)
    num_classes = len(classes)
    print(f"Processing images in folder: {folder_path}")

    image_files = [filename for filename in os.listdir(folder_path) if filename.endswith(('.png'))]
    args_list = [(os.path.join(folder_path, filename), label_path, num_classes) for filename in image_files if filename.endswith(('.png'))]

    with Pool(num_processes) as pool:
        pool.map(process_image_wrapper, args_list)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Label images from source to destination.")
    parser.add_argument("--source", type=str, help="Source folder containing images")
    parser.add_argument("--dest", type=str, help="Destination folder for labels")
    parser.add_argument("--classes", type=str, help=".txt file containing classes")
    args = parser.parse_args()

    process_images_parallel_in_folder(args, num_processes=10)
