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

exif_tag = 'datetime'

hashs = ['puzzle', 'phash', 'whash']

rule_to_apply = 'three_similar_concurrent'
rule_args = (40, pd.Timedelta(days = 1), 'whash')

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
if not os.path.exists(c_m_photos_path + 'suggestions/'):
    os.mkdir(c_m_photos_path + 'suggestions/')

def cpy_all_photos_in_list(list_of_photos, user_id, counter):
    dst_path = c_m_photos_path + 'suggestions/{}/{}/'.format(user_id, counter)
    
    if not os.path.exists(dst_path):
        os.makedirs(dst_path)
    
    for image in list_of_photos:
        shutil.copy(c_m_photos_path + image + '.jpg', dst_path + image + '.jpg')

def store_suggestions(user_id, lst):
    for i, ls in enumerate(lst):
        cpy_all_photos_in_list(ls, user_id, i)
    
for user_id, lst in zip(suggestions[:10].index, suggestions[:10].values):
    store_suggestions(user_id, lst)

#Create timeline of suggestions

#Compute metrics on step photos (% covered)

#Present c+m suggestions for manual review? (Feasible?)