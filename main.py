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
suggestions_fldr_name = 'suggestions_9/'

exif_tag = 'datetime'

hashs = ['puzzle', 'phash', 'whash']

rule_to_apply = 'three_s_c_with_min_time_diff'
rule_args = ('user', 20, pd.Timedelta(hours = 2.5), 7/6., 'whash')

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

def create_photo_list(list_of_photos, user_id, counter):
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
        create_photo_list(ls, user_id, i)
        
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
#            if suggestion_time > dt.datetime(2500,1,1):
#                
            timeline.append(suggestion_time)
        #Convert to pandas Series
        timeline = pd.Series([1]*len(timeline), index = timeline, name=user_fldr.split('/')[-1])
        timeline = timeline.resample(granularity).sum()
        all_timelines.append(timeline)
        
    all_timelines = pd.concat(all_timelines, axis = 1)
    return all_timelines
    
timeline = suggestions_timeline(c_m_photos_path + suggestions_fldr_name, c_m_photos_db)   

####Time to calc precsion and recall####
#Get all manually labelled recipes in c and m photos
def parse_label(fldr_path):
    with open(fldr_path + 'label.txt', 'r') as f:
        recipe = f.readline()
        if recipe == 'recipe\n':
            lines = f.readlines()
        else:
            lines = []
    
    lines = [l.strip() for l in lines]
    indexs = [i for i,v in enumerate(lines) if v.startswith('.')]
    indexs.append(len(lines))
    list_of_recipes = [lines[indexs[i]+1:indexs[i+1]] for i in range(len(indexs)-1)]
                       
    return list_of_recipes
    
all_recipes = {}

for user_id in cm_users:
    usr_fldr = c_m_photos_path + 'by_user/' + str(user_id) + '/'
    recipes = parse_label(usr_fldr)
    all_recipes[usr_fldr.split('/')[-2]] = recipes

total_recipes = sum([len(v) for v in all_recipes.values()])
                
#How do we decide we made a 'correct' suggestion?
#correct conditions
# - all photos are subset of 1 recipe
# - X photos not in the recipe (X probably has to equal 1) (keep track of this)
# - Must be a certain % of recipe? (% ~= 75) <- interesting to see how this changes rating

def is_suggestion_recipe(suggestion, user_recipes, max_extra = 1, min_percentage = .75):
    """suggestion is a list of image ids making a suggestion by the logic
    user_recipes is a list of lists of image ids, detailing all the recipes
    identitified in the user's photos"""
    #Bools to show if we ever meet the condidtions individually, but not in 
    #the same recipe
    best_extra_photos = False
    best_suff_cover = False
    for recipe in user_recipes:
        no_extra_photos = False
        suff_cover = False
    
        matches = sum([i in recipe for i in suggestion])
        extra_photos = len(suggestion) - matches
        percentage = float(matches) / len(recipe)
        if extra_photos <= max_extra:
            no_extra_photos = True
            best_extra_photos = True
        if percentage > min_percentage:
            suff_cover = True
            best_suff_cover = True
        if no_extra_photos and suff_cover:
            #We matched to a labelled recipe - no need to check the others
            break
    
    return [best_extra_photos, best_suff_cover]

def eval_users_suggestions(suggestions, user_id, all_user_recipes):
    user_recipes = all_user_recipes[user_id]
    if not user_recipes:
        #No recipes => all suggestions are false
        results = [[False, False]]*len(suggestions)
        return results
    results = []
    for suggestion in suggestions:
        results.append(is_suggestion_recipe(suggestion, user_recipes))
        
    return results

#Finally - eval all our suggestions to see if they were correct
   
results = pd.Series(index = suggestions.index)
#Some bullshit to get around lists as elements in pandas
results.iloc[0] = [[False,False]]
results.iloc[0] = []
#Have to do this to get around apply treating lists as special cases
for u_id in results.index:
    results.loc[u_id] = eval_users_suggestions(suggestions[u_id], str(u_id), all_recipes)
recipe_finds = results.map(lambda x: [li[0] and li[1] for li in x])
extra_photos = results.map(lambda x: [li[0] for li in x])
suff_cover = results.map(lambda x: [li[1] for li in x])

#Calc some metrics
total_suggestions = recipe_finds.apply(lambda x: len(x) if x else pd.np.NAN).sum()
total_recipe_finds = recipe_finds.apply(lambda x: sum(x) if x else pd.np.NAN).sum()
precision = total_recipe_finds/float(total_suggestions)
recall = total_recipe_finds/float(total_recipes)