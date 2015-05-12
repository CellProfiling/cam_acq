import os
import fnmatch
import re
import tifffile
import abc
from collections import defaultdict

class Base(object):
    """Base class

    Attributes:
        path: A string representing the path to the object.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, path):
        self.path = path

    def get_dir(self):
        """Return parent directory."""
        return os.path.dirname(self.path)

    @abc.abstractmethod
    def get_name(self, path, regex):
        """Return the part of the name of the object, matching regex."""
        match = re.search(regex, os.path.basename(path))
        if match:
            return match.group()
        else:
            print('No match')
            return None

    def cut_path(self, regex):
        """Remove part of path name matching regex, and return result."""
        return re.sub(regex, '', self.path)

    @abc.abstractmethod
    def base_type(self):
        """"Return a string representing the type of object this is."""
        pass

class Directory(Base):
    """A directory on the plate."""

    def get_children(self):
        """Return a list of child directories."""
        return filter(os.path.isdir, [os.path.join(self.path,f)
                      for f in os.listdir(self.path)])

    def get_all_children(self):
        dir_list = []
        for root, dirnames, filenames in os.walk(self.path):
            for dirname in dirnames:
                dir_list.append(os.path.join(root, dirname))
        return dir_list

    def get_name(self, regex):
        """Return the part of the name of the current directory,
        matching regex."""
        path = os.path.normpath(self.path)
        return super(Directory, self).get_name(path, regex)

    def get_files(self, regex):
        return filter(os.path.isfile, [os.path.join(self.path,f)
                      for f in fnmatch.filter(os.listdir(self.path), regex)])

    def get_all_files(self, regex):
        """Return a list of all files matching regex, recursively."""
        file_list = []
        for root, dirnames, filenames in os.walk(self.path):
            for filename in fnmatch.filter(filenames, regex):
                file_list.append(os.path.join(root, filename))
        return file_list

    def base_type(self):
        """"Return a string representing the type of object this is."""
        return 'directory'

class File(Base):
    """A file.
    """

    def read_csv(self, index, keys):
        list_dict = defaultdict(list)
        with open(self.path) as f:
            reader = csv.DictReader(f)
            for d in reader:
                for key in keys:
                    list_dict[d[index]].append(d[key])

    def write_csv(self, dict_list, keys):
        """Function to write a list of dicts as a csv file.
        dict_list: A list of dicts, each having the same keys as keys param.
        keys: A list of strings to order the keys as column headers
        """

        with open(self.path, 'wb') as f:
            w = csv.DictWriter(f, keys)
            w.writeheader()
            w.writerows(dict_list)

    def get_name(self, regex):
        """Return the part of the name of the file, matching regex."""
        return super(File, self).get_name(self.path, regex)

    def base_type(self):
        """"Return a string representing the type of object this is."""
        return 'file'

class CamImage(Base):
    """An image.
    """

    def read_image(self):
        """Read a tif image and return the data."""
        with tifffile.TiffFile(self.path) as tif:
            return tif.asarray()

    def meta_data(self):
        """Read a tif image and return the meta data of the description."""
        with tifffile.TiffFile(self.path) as tif:
            return tif[0].image_description

    def save_image(self, data, metadata=None):
        """Save a tif image with image data and meta data."""
        #if metadata is None: # description not always needed
        #    metadata = ''
        tifffile.imsave(self.path, data, description=metadata)

    def get_name(self, regex):
        """Return the part of the name of the file, matching regex."""
        return super(File, self).get_name(self.path, regex)

    def base_type(self):
        """"Return a string representing the type of object this is."""
        return 'image'
