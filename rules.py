#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 16:50:53 2016

@author: oisin-brogan

Logics to try identify a group of step photos in a users stream of classified
and moderated photos.
"""

import pandas as pd, datetime as dt
import sys
sys.path.append('/Users/oisin-brogan/Code/similar_images')
from process_results import load_dictionary
import pypuzzle

#Common data preperation steps/metrics
#EXIF datetime
def convert_exif_to_datetime(exif_time_string):
    try:
        return dt.datetime.strptime(exif_time_string, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        print 'Failed on {}'.format(exif_time_string)
        return pd.np.NAN    
    
def convert_ckpd_to_datetime(time_string):
    try:
        return dt.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        print 'Failed on {}'.format(time_string)
        return pd.np.NAN    

def total_diff(dt_column):
    return max(dt_column) - min(dt_column)

def diffs(dt_column):
    sort = sorted(dt_column.values)
    diffs = pd.np.diff(sort)
    return diffs
    
#Hashes
def compute_all_diffs(fldr_path, hash_name):    
    if hash_name == "puzzle":
        puzzle = pypuzzle.Puzzle()

    hash_dictionary = load_dictionary(fldr_path + '%s.txt' % hash_name)
    diffs = pd.DataFrame(index = hash_dictionary.keys(), columns =hash_dictionary.keys())
    for key in hash_dictionary.keys():
        for k in hash_dictionary.keys():
            if hash_name == 'puzzle':
                #removing .jpg
                diffs.loc[key[:-4], k[:-4]] = puzzle.get_distance_from_cvec(hash_dictionary[key],hash_dictionary[k])
            else:
                #Removing .jpg
                diffs.loc[key[:-4], k[:-4]] = hash_dictionary[key] - hash_dictionary[k]
    return diffs    

def max_min_avg_median_diffs(diffs_dictionary):
    flatten_list = [item for sublist in diffs_dictionary.values() for item in sublist]
    return pd.Series([max(flatten_list), min(flatten_list), pd.np.mean(flatten_list), pd.np.median(flatten_list)])

#SP exploring
    
#C_M Rules

def three_similar_concurrent(db, db_type, max_allow_hash_diff, total_time, hash_type):
    chronolical = db.sort('taken_at')
    if db_type == 'user':
        hdiffs = compute_all_diffs('/Users/oisin-brogan/Downloads/moderated_photos/by_user/'
                               + str(db.user_id.values[0]) + '/', hash_type)
    elif db_type == 'recipe':
        hdiffs = compute_all_diffs('/Users/oisin-brogan/Downloads/step_photos2/by_recipe/'
                               + str(db.recipe_id.values[0]) + '/', hash_type)
    else:
        print "Invalid db_type!"
        return
        
    suggestions = []
    
    for time in chronolical.taken_at.values:
        time_diffs = chronolical.taken_at - time
        within_window = chronolical[(time_diffs < total_time) & (time_diffs >= pd.Timedelta(0))]
        if within_window.shape[0] < 3:
            #Looking for at least 3 photo steps
            continue
        #Got a group to test
        relevent_hdiffs = hdiffs.loc[within_window.image_id.values.tolist(),
                                     within_window.image_id.values.tolist()]
        max_hdiff = relevent_hdiffs.max().max()
        #Remove the largest diff until you're below the max_allowed
        while max_hdiff > max_allow_hash_diff:
            vertix_one = relevent_hdiffs.max().idxmax()
            vertix_two = relevent_hdiffs.loc[relevent_hdiffs.max().idxmax()].idxmax()
            #max_hdiff is bewteen two photos - we choose to remove the photo
            #the least similar to all the other photos
            if sum(relevent_hdiffs.loc[vertix_one]) < sum(relevent_hdiffs.loc[vertix_two]):
                relevent_hdiffs = relevent_hdiffs.drop(vertix_two)
                relevent_hdiffs = relevent_hdiffs.drop(vertix_two, axis = 1)
            else:
                relevent_hdiffs = relevent_hdiffs.drop(vertix_one)
                relevent_hdiffs = relevent_hdiffs.drop(vertix_one, axis = 1)
            
            if relevent_hdiffs.shape[0] < 3:
                #i.e. if we've less then 3 photos left
                break
                #there's nothing for us here
            max_hdiff = relevent_hdiffs.max().max() 
        if relevent_hdiffs.shape[0] > 3:
            possibility = set(relevent_hdiffs.columns)
            #Check if this possibility is a subset of any previous suggestion
            if sum([possibility <= s for s in suggestions]) == 0:
                suggestions.append(possibility)
    
    return suggestions
            
rule_dict = {'three_similar_concurrent' : three_similar_concurrent}
            
    