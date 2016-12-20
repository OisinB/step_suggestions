import Tkinter as tk
from PIL import ImageTk, Image
from math import floor
import os
from rules import convert_ckpd_to_datetime
import pandas as pd, datetime as dt
import argparse

root = tk.Tk()
root.withdraw()

current_window = None
current_canvas = None

def  replace_window(root):
    """Destroy current window, create new window"""
    global current_window
    if current_window is not None:
        current_window.destroy()
    current_window = tk.Toplevel(root)

    # if the user kills the window via the window manager,
    # exit the application. 
    current_window.wm_protocol("WM_DELETE_WINDOW", root.destroy)

    return current_window

def onFrameConfigure(canvas):
    '''Reset the scroll region to encompass the inner frame'''
    canvas.configure(scrollregion=canvas.bbox("all"))

def write_label(is_recipe):
    global fldr
    global folders
    with open(fldr + '/label.txt', 'w') as f:
        if is_recipe:
            print "Labelling recipe"
            f.write('recipe\n')
        else:
            print "Labelling as non-recipe"
            f.write('not_recipe\n')
    #Update to next folder
    try:
        index = folders.index(fldr)
        fldr = folders[index+1]
    except IndexError:
        #We've reached the end of the folders list
        root.destroy()
        return
    window_of_images()

def look_up_chronological(images):
    db = pd.read_csv('/Users/oisin-brogan/Downloads/moderated_photos/db.csv')
    db.taken_at = db.taken_at.map(convert_ckpd_to_datetime)
    db = db.set_index('image_id')
    
    ordered = []
    for i in images:
        time = db.loc[i[:-4]].taken_at
        ordered.append((i, time))
    ordered = sorted(ordered, key = lambda x: x[1])
    
    return ordered
            
#fldr = "/Users/oisin-brogan/Downloads/moderated_photos/suggestions/2458250/2/"
def window_of_images():
    global fldr
    images = [f for f in os.listdir(fldr) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    images = [i[0] for i in look_up_chronological(images)]
              
    window = replace_window(root)
    canvas = tk.Canvas(window, borderwidth=0, background="#ffffff")
    frame = tk.Frame(canvas, background="#ffffff")
    vsb = tk.Scrollbar(window, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((4,4), window=frame, anchor="nw")
    
    frame.bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))

    window.title("Manual Recipe Review")
    window.geometry("{0}x{1}".format((320*4)+10, (len(images)*320/4)+1))
    window.configure(background='grey') 
    
    resized = []
    
    for c, f in enumerate(images):
        #Creates a Tkinter-compatible photo image, which can be used everywhere Tkinter expects an image object.
        img = Image.open(fldr + '/' + f)
        
        width, height = img.size
        size = 300
        
        if width < height:
            ratio = float(width) / float(height)
            newwidth = ratio * size
            img = img.resize((int(floor(newwidth)), size), Image.ANTIALIAS)
        
        elif width > height:
            ratio = float(height) / float(width)
            newheight = ratio * size
            img = img.resize((size, int(floor(newheight))), Image.ANTIALIAS)
        
        imgTK = ImageTk.PhotoImage(img)
        resized.append(imgTK)
    
        #The Label widget is a standard Tkinter widget used to display a text or image on the screen.
        panel = tk.Label(frame, image = resized[c])
        
        #The grid geometry manager packs widgets in rows or columns.
        panel.grid(row=c/4, column=c%4, padx = 10, pady = 10)
    
    yes_button = tk.Button(frame, text="Recipe", command=lambda: write_label(True))
    no_button = tk.Button(frame, text="Not recipe", command=lambda: write_label(False))
    
    yes_button.grid(row=(len(images)/4)+1, column=0)
    no_button.grid(row=(len(images)/4)+2, column=0)
    
    #Start the GUI
    window.mainloop()

parser = argparse.ArgumentParser()
    
parser.add_argument(
    '--user_id',
    type=str,
    default='2458250',
    help='Id for single user to label'
)

parser.add_argument(
    '--user_path',
    type=str,
    default='/Users/oisin-brogan/Downloads/moderated_photos/suggestions/2458250/',
    help='Id for single user to label'
)

parser.add_argument(
    '--suggestion_folder',
    type=str,
    default='/Users/oisin-brogan/Downloads/moderated_photos/suggestions/',
    help='Path to top level suggestion folder'
)

parser.add_argument(
    '--user_or_all',
    type=str,
    default='user',
    help='Parse a single user or all available suggestions'
)

FLAGS, unparsed = parser.parse_known_args()

if FLAGS.user_or_all == 'user':
    user_folder = '/Users/oisin-brogan/Downloads/moderated_photos/suggestions/' + FLAGS.user_id
    folders = [os.path.join(user_folder,f) for f in os.listdir(user_folder)
            if os.path.isdir(os.path.join(user_folder,f))]
else:
    #Parse all suggestions
    folders = []
    for top,dirs,files in os.walk(FLAGS.suggestion_folder):
        #If we're at the bottom
        if not dirs:
            folders.append(top)
            
fldr = folders[0]
print folders
window = window_of_images()