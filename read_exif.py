from os import listdir
from os.path import isfile, join
import sys
import exifread


def read_exif(look_for, image_path, results_file):
    onlyfiles = [f for f in listdir(image_path) if join(image_path, f).lower().endswith(('.png', '.jpg', '.jpeg'))]
    results = ""

    for imagefile in onlyfiles:
        f = open(image_path + '/' + imagefile, 'rb')
        results += image_path + '/' + imagefile + '\n'
        try:
            tags = exifread.process_file(f)
        except:
            import traceback
            print "{} failed to read exif".format(imagefile)
            traceback.print_exc()
            results = ""
            continue
        for tag in tags.keys():
            if tag.lower().find(look_for) != -1:
                results += "Key: %s, value %s" % (tag, tags[tag]) + '\n'
        try:
            write_to_file(results_file, results)
        except:
            print "Write fail. {0}{1}".format(image_path, imagefile)
        results = ""

def write_to_file(filename, results_string):
    with open(filename, 'a') as f:
        f.write(results_string)
    f.close()

if __name__ == '__main__':
    read_exif(sys.argv[1], sys.argv[2], sys.argv[3])
