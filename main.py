#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 11:08:32 2016

@author: oisin-brogan
"""
import pandas as pd, datetime as dt
import os, sys, shutil
sys.path.append('/Users/oisin-brogan/Code/similar_images')
from generate_hashes import generate_hashes
from process_results import load_dictionary
from read_exif import read_exif
import rules

###Parameters#### Final version will parse from terminal
step_photos_path = '/Users/oisin-brogan/Downloads/step_photos2/'
c_m_photos_path = '/Users/oisin-brogan/Downloads/moderated_photos/'
suggestions_fldr_name = 'suggestions_1/'

exif_tag = 'datetime'

hashs = ['puzzle', 'phash', 'whash']

rule_to_apply = 'three_similar_concurrent'
rule_args = ('user', 20, pd.Timedelta(hours = 12), 'whash')

####Prepare data####
#Load in step photos data
step_photos_db = pd.read_csv(step_photos_path + 'db.csv')
c_m_photos_db = pd.read_csv(c_m_photos_path + 'db.csv')

#Load in classified and moderated photos

#Read EXIF data
read_exif(exif_tag, step_photos_path, step_photos_path + 'exif_data.txt')

def read_exif_txt(txt_path):
    datetimes = {}
    with open(txt_path, 'r') as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith('/'):
            key = line.split('//')[1][:-5] #getting just image id
            datetimes[key] = ""
        else:
            datetimes[key] = line.split('value ')[1].strip()
    return datetimes
    
def add_taken_at(db, txt_path):
    df = db.copy()
    dic = read_exif_txt(txt_path)
    series = pd.Series(dic)
    df = df.set_index('image_id')
    df.loc[:, 'taken_at'] = series
    df = df.reset_index()
    
    return df

step_photos_db = add_taken_at(step_photos_db, step_photos_path + 'exif_data.txt')

#Convert time strings to  datetimes
step_photos_db.taken_at = step_photos_db.taken_at.map(rules.convert_exif_to_datetime)
c_m_photos_db.taken_at = c_m_photos_db.taken_at.map(rules.convert_ckpd_to_datetime)

#Hashes    
#Store step photos in recipe spefic dirs (if not already done so)
sp_recipes = set(step_photos_db.recipe_id)
for recipe_id in sp_recipes:
    recipe_fldr = step_photos_path + 'by_recipe/' + str(recipe_id)
    if not os.path.exists(recipe_fldr):
        print "Moving to recipe folder {}".format(recipe_id)
        os.makedirs(recipe_fldr)
        relevant_photos = step_photos_db[step_photos_db.recipe_id == recipe_id]['image_id'].values
        for image_id in relevant_photos:
            shutil.copyfile(step_photos_path + str(image_id) + '.jpg',
                            recipe_fldr + '/' + str(image_id) + '.jpg')
    #else we assume the photos have already been moved - do nothing

#Store c+m photos in user spefic dirs (if not already done so)
cm_users = set(c_m_photos_db.user_id)
for user_id in cm_users:
    usr_fldr = c_m_photos_path + 'by_user/' + str(user_id)
    if not os.path.exists(usr_fldr):
        print "Moving to user folder {}".format(user_id)
        os.makedirs(usr_fldr)
        relevant_photos = c_m_photos_db[c_m_photos_db.user_id == user_id]['image_id'].values
        for image_id in relevant_photos:
            shutil.copyfile(c_m_photos_path + str(image_id) + '.jpg',
                            usr_fldr + '/' + str(image_id) + '.jpg')
    #else we assume the photos have already been moved - do nothing


#Generate required hashes
for recipe_id in sp_recipes:
    recipe_fldr = step_photos_path + 'by_recipe/' + str(recipe_id) + '/'
    for h in hashs:
        if not os.path.exists(recipe_fldr + '{}.txt'.format(h)): #Don't repeat work
            generate_hashes(h, recipe_fldr, recipe_fldr + '{}.txt'.format(h))

for user_id in cm_users:
    usr_fldr = c_m_photos_path + 'by_user/' + str(user_id) + '/'
    for h in hashs:
        if not os.path.exists(usr_fldr + '{}.txt'.format(h)): #Don't repeat work
            generate_hashes(h, usr_fldr, usr_fldr + '{}.txt'.format(h))
            
####Apply Rule#####
#Load the asked for rule
rule = rules.rule_dict[rule_to_apply]
#Apply rule with parameters
c_m_by_user = c_m_photos_db.groupby('user_id')
suggestions = c_m_by_user.apply(rule, *rule_args)

####Performance metrics####
#Store suggestions
if not os.path.exists(c_m_photos_path + suggestions_fldr_name):
    os.mkdir(c_m_photos_path + suggestions_fldr_name)

def cpy_all_photos_in_list(list_of_photos, user_id, counter):
    dst_path = c_m_photos_path + suggestions_fldr_name + '{}/{}/'.format(user_id, counter)
    
    if not os.path.exists(dst_path):
        os.makedirs(dst_path)
    
    #Create text file with the image ids
    with open(dst_path+'image_list.txt', 'w') as f:
        for image in list_of_photos:
            f.write(image + '.jpg\n')

#Store the suggestions in seperate folders
for user_id, lst in zip(suggestions.index, suggestions.values):
    for i, ls in enumerate(lst):
        cpy_all_photos_in_list(ls, user_id, i)
#Create timeline of suggestions
def suggestions_timeline(all_suggestion_folder, cm_db, granularity='D'):
    df = cm_db.copy()
    df = df.set_index('image_id')
    
    all_timelines = []
    
    users_with_suggestions = [os.path.join(all_suggestion_folder,f) for f in 
                    os.listdir(all_suggestion_folder) if 
                    os.path.isdir(os.path.join(all_suggestion_folder,f))]
    for user_fldr in users_with_suggestions:            
        user_suggestions = [os.path.join(user_fldr,f) for 
                        f in os.listdir(user_fldr)
                        if os.path.isdir(os.path.join(user_fldr  ,f))]
        timeline = []
        for suggestion_fldr in user_suggestions:
            #Read txt file of image id
            if os.path.exists(suggestion_fldr + '/image_list.txt'):
                with open(suggestion_fldr + '/image_list.txt', 'r') as f:
                    images = [i[:-5] for i in f.readlines()]
            else:
                print "Missing image list file in {}".format(suggestion_fldr)
                continue
            #Take the time of the last photo as the suggestion time for
            times = df.loc[images].taken_at
            suggestion_time = max(times)
            timeline.append(suggestion_time)
        #Convert to pandas Series
        timeline = pd.Series([1]*len(timeline), index = timeline, name=user_fldr.split('/')[-1])
        timeline = timeline.resample(granularity).sum()
        all_timelines.append(timeline)
        
    all_timelines = pd.concat(all_timelines, axis = 1)
    return all_timelines
    
timeline = suggestions_timeline(c_m_photos_path + suggestions_fldr_name, c_m_photos_db)   

#Compute metrics on step photos (% covered)

#Present c+m suggestions for manual review? (Feasible?)

def calc_accuracy(all_suggestion_folder):
    correct_labels = []
    for root, dirs, files in os.walk(all_suggestion_folder):
        if not dirs: #We're at the bottom folder
            with open(root + '/label.txt') as f:
                label = f.read()
                correct_labels.append(label == 'recipe\n')
    return correct_labels
    
results = calc_accuracy(c_m_photos_path + suggestions_fldr_name)
accuracy = sum(results)/float(len(results))