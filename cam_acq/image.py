import os
import fnmatch
import re
import tifffile
import abc
from collections import defaultdict
from scipy.misc import imread
import numpy as np


def check_list(fnc):
    """Decorator function for the functions in the Base class
    and its subclasses."""

    def wrapper(self, *args, **kwargs):
        """Wrapper function in the decorator.
        Runs the function fnc for all paths in path_list and returns
        a list with the result."""
        result = []
        for path in self.path_list:
            self.path = path
            result.append(fnc(self, *args, **kwargs))
        return result
    return wrapper


class Base(object):

    """Base class

    Attributes:
        path: A string representing the path to the object.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, path_list):
        self.path_list = path_list
        self.path = None

    @check_list
    def get_dir(self):
        """Return parent directory."""
        return os.path.dirname(self.path)

    @check_list
    @abc.abstractmethod
    def get_name(self, path, regex):
        """Return the part of the name of the object, matching regex."""
        match = re.search(regex, os.path.basename(path))
        if match:
            return match.group()
        else:
            print('No match')
            return None

    @check_list
    def cut_path(self, regex):
        """Remove part of path name matching regex, and return result."""
        return re.sub(regex, '', self.path)

    @check_list
    @abc.abstractmethod
    def base_type(self):
        """"Return a string representing the type of object this is."""
        pass


class Directory(Base):

    """A directory on the plate."""

    @check_list
    def get_children(self):
        """Return a list of child directories at path."""
        return filter(os.path.isdir, [os.path.join(self.path, f)
                                      for f in os.listdir(self.path)])

    @check_list
    def get_all_children(self):
        """Return a recursive list of child directories at path."""
        dir_list = []
        for root, dirnames, filenames in os.walk(self.path):
            for dirname in dirnames:
                dir_list.append(os.path.join(root, dirname))
        return dir_list

    @check_list
    def get_name(self, regex):
        """Return the part of the name of the current directory,
        matching regex, at path."""
        path = os.path.normpath(self.path)
        return super(Directory, self).get_name(path, regex)

    @check_list
    def get_files(self, regex):
        """Return a list of all files matching regex at path."""
        return filter(os.path.isfile,
                      [os.path.join(self.path, f)
                       for f in fnmatch.filter(os.listdir(self.path), regex)])

    @check_list
    def get_all_files(self, regex):
        """Return a list of all files matching regex, recursively, at path."""
        file_list = []
        for root, dirnames, filenames in os.walk(self.path):
            for filename in fnmatch.filter(filenames, regex):
                file_list.append(os.path.join(root, filename))
        return file_list

    @check_list
    def base_type(self):
        """"Return a string representing the type of object this is."""
        return 'directory'


class File(Base):

    """A file.
    """

    @check_list
    def read_csv(path, index, header):
        """Read a csv file and return a defaultdict of lists."""
        dict_list = defaultdict(list)
        with open(path) as f:
            reader = csv.DictReader(f)
            for d in reader:
                for key in header:
                    dict_list[d[index]].append(d[key])
        return dict_list

    @check_list
    def write_csv(path, d, header):
        """Function to write a defaultdict of lists as a csv file."""
        with open(path, 'wb') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for key, value in d.iteritems():
                writer.writerow([key] + value)
        return

    @check_list
    def get_name(self, regex):
        """Return the part of the name of the file, matching regex."""
        return super(File, self).get_name(self.path, regex)

    @check_list
    def base_type(self):
        """"Return a string representing the type of object this is."""
        return 'file'


class CamImage(Base):

    """An image.
    """

    # FIXME: Add init to create image id attributes: Channel, z slice etc.

    # def read_image(self):
    #    """Read a tif image and return the data."""
    #    with tifffile.TiffFile(self.path) as tif:
    #        return tif.asarray()

    @check_list
    def read_image(self, path=None):
        """Read a tif image and return the data."""
        if path is None:
            path = self.path
        return imread(path)

    @check_list
    def meta_data(self):
        """Read a tif image and return the meta data of the description."""
        with tifffile.TiffFile(self.path) as tif:
            return tif[0].image_description

    @check_list
    def save_image(self, data, metadata=None):
        """Save a tif image with image data and meta data."""
        # if metadata is None: # description not always needed
        #    metadata = ''
        tifffile.imsave(self.path, data, description=metadata)
        return

    @check_list
    def get_name(self, regex, path=None):
        """Return the part of the name of the file, matching regex."""
        if path is None:
            path = self.path
        return super(File, self).get_name(path, regex)

    def make_proj(self):
        """Function to make a dict of max projections from a list of paths
        to images. Each channel will make one max projection"""
        channels = []
        print('Making max projections')
        ptime = time.time()
        sorted_images = defaultdict(list)
        max_imgs = {}
        for path in self.path_list:
            channel = self.get_name('C\d\d', path=path)
            sorted_images[channel].append(self.read_image(path))
            max_imgs[channel] = np.maximum.reduce(sorted_images[channel])
        print('Max proj:' + str(time.time() - ptime) + ' secs')
        return max_imgs

    # FIXME: Finish adding functions for image handling and processing.

    @check_list
    def base_type(self):
        """"Return a string representing the type of object this is."""
        return 'image'
