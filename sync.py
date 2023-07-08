import os
import subprocess
import datetime
import time
import sys

from path import Path
from setup import Setup

class Sync(Setup):

    def __init__(self, android_path, pc_path):
        self.android_path = android_path
        self.pc_path = pc_path

    @staticmethod
    def check_adb_connection():
        """Establish connection with the android device"""
        output = subprocess.check_output(["adb", "devices"]).decode()
        lines = output.strip().split('\n')
        if len(lines) > 1:
            devices = lines[1:]
            for device in devices:
                if "device" in device:
                    continue
        else:
            print("Android device cannot be found through adb connection")
            time.sleep(3)
            sys.exit(0)
   
    @staticmethod
    def check_pc_os():
        """Identify the PC os"""
        if os.name == "posix":
            Setup.current_pc_os = Path.LINUX
        elif os.name == "nt":
            Setup.current_pc_os = Path.WINDOWS
        else:
            print("The PC operating system is not supported")
            time.sleep(3)
            sys.exit(0)

    @staticmethod
    def pull_files_from_android(path_list):
        for path in path_list:
            source_path = path
            destination_path = os.path.join(Sync.current_pc_rootpath, os.path.basename(os.path.dirname(source_path)))
            command = ["adb", "pull", source_path, destination_path]
            process = subprocess.run(command, capture_output=True, text=True)
            if process.stdout:
                print("Sync:", process.stdout, end="")
            if process.stderr:
                print("Error:", process.stderr, end="")
        
    @staticmethod
    def push_files_to_android(path_list):
        for path in path_list:
            source_path = path
            destination_path = os.path.join(Sync.current_android_rootpath,  os.path.basename(os.path.dirname(source_path))).replace("\\", "/")
            command = ["adb", "push", source_path, destination_path]
            process = subprocess.run(command, capture_output=True, text=True)
            if process.stdout:
                print("Sync:", process.stdout, end="")
            if process.stderr:
                print("Error:", process.stderr, end="")

    def compare_dates(android_path_date_list, pc_path_date_list):
        """Compare each dictionaries in the list, if a match is found then the the latest last modification date 
        will overwrite to the other platform. If a unique file is found, then it will be copied over."""
        copy_to_android = []
        copy_to_pc = []
        
        for pc_path_date in pc_path_date_list:
            pc_date = pc_path_date["last_modified"]
            pc_path = pc_path_date["file_path"]
            for android_path_date in android_path_date_list:
                android_date = android_path_date["last_modified"]
                android_path = android_path_date["file_path"]

                if os.path.basename(pc_path) == os.path.basename(android_path):
                    if pc_date > android_date:
                        copy_to_android.append(pc_path)
                    elif pc_date < android_date:
                        copy_to_pc.append(android_path)
                    break 

        for android_path_date in android_path_date_list:
            android_path = android_path_date["file_path"]
            android_filename = os.path.basename(android_path)
            if not any(android_filename == os.path.basename(entry["file_path"]) for entry in pc_path_date_list):
                print(f"A new file is synced from android: {android_path}")
                copy_to_pc.append(android_path)

        for pc_path_date in pc_path_date_list:
            pc_path = pc_path_date["file_path"]
            pc_filename = os.path.basename(pc_path)
            if not any(pc_filename == os.path.basename(entry["file_path"]) for entry in android_path_date_list):
                print(f"A new file is synced from pc: {pc_path}")
                copy_to_android.append(pc_path)
        
        return copy_to_android, copy_to_pc

    def get_modified_dates(self):
        '''Extract the file paths and its last modified dates, placing the pair in a dictionary, then to a list.'''
        android_path_date_list = []
        command = ["adb", "shell", "ls", self.android_path]
        process = subprocess.run(command, capture_output=True, text=True)
        file_list = process.stdout.splitlines()
        for file in file_list:
            filename, extension = os.path.splitext(file)
            if not Sync.is_valid_extension(extension):
                continue
            file_path =  os.path.join(self.android_path, file).replace("\\", "/")
            command = ["adb", "shell", "stat", "-c", "%y", file_path]
            process = subprocess.run(command, capture_output=True, text=True)
            output = process.stdout.strip()
            last_modified = datetime.datetime.strptime(output[:19], "%Y-%m-%d %H:%M:%S")
            last_modified = last_modified.strftime("%Y-%m-%d %H:%M:%S")
            android_path_date_dict = {}
            android_path_date_dict["file_path"] = file_path
            android_path_date_dict["last_modified"] = last_modified
            android_path_date_list.append(android_path_date_dict)
        
        pc_path_date_list = []
        file_list = os.listdir(self.pc_path)
        for file in file_list:
            filename, extension = os.path.splitext(file)
            if not Sync.is_valid_extension(extension):
                continue
            file_path = os.path.join(self.pc_path, file)
            last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            last_modified = last_modified.strftime("%Y-%m-%d %H:%M:%S")
            pc_path_date_dict = {}
            pc_path_date_dict["file_path"] = file_path
            pc_path_date_dict["last_modified"] = last_modified
            pc_path_date_list.append(pc_path_date_dict)
    
        return android_path_date_list, pc_path_date_list
    
    def execute_sync(self):
        android_path_date_list, pc_path_date_list = Sync.get_modified_dates(self) 
        copy_to_android, copy_to_pc = Sync.compare_dates(android_path_date_list, pc_path_date_list)
        Sync.push_files_to_android(copy_to_android)
        Sync.pull_files_from_android(copy_to_pc)
        
    
    