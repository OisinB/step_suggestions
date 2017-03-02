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
#import pypuzzle
from functools import reduce

#Common data preperation steps/metrics
#EXIF datetime
def convert_exif_to_datetime(exif_time_string):
    try:
        time_taken = dt.datetime.strptime(exif_time_string, "%Y:%m:%d %H:%M:%S")
        if time_taken > dt.datetime.today(): #Can't be from the future
            #Guess it's from this year
            this_year = dt.datetime.today().year
            time_taken = dt.datetime.strptime(str(this_year) + exif_time_string[4:],
                                              "%Y:%m:%d %H:%M:%S")
            if time_taken > dt.datetime.today(): #Can't be from the future
                #Settle on last year
                time_taken = dt.datetime.strptime(str(this_year-1) + exif_time_string[4:],
                                              "%Y:%m:%d %H:%M:%S")
        return time_taken
    except ValueError:
        print('Failed on {}'.format(exif_time_string))
        return pd.np.NAN    
    
def convert_ckpd_to_datetime(time_string):
    try:
        time_taken = dt.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S")
        if time_taken > dt.datetime.today(): #Can't be from the future
            #Guess it's from this year
            this_year = dt.datetime.today().year
            time_taken = dt.datetime.strptime(str(this_year) + time_string[4:],
                                              "%Y-%m-%dT%H:%M:%S")
            if time_taken > dt.datetime.today(): #Can't be from the future
                #Settle on last year
                time_taken = dt.datetime.strptime(str(this_year-1) + time_string[4:],
                                              "%Y-%m-%dT%H:%M:%S")
        return time_taken
    except ValueError:
        print('Failed on {}'.format(time_string))
        return pd.np.NAN    

def total_diff(dt_column):
    return max(dt_column) - min(dt_column)
    
#Hashes
def compute_all_diffs(fldr_path, hash_name):    
    if hash_name == "puzzle":
        puzzle = pypuzzle.Puzzle()

    hash_dictionary = load_dictionary(fldr_path + '%s.txt' % hash_name)
    diffs = pd.DataFrame()
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

#### Support Algo ####

#Duplicate photo removal

def set_up_db_groups(db):
    #Set up for grouping dups
    dup_groups = db.image_id.tolist()
    dup_groups = [[x] for x in dup_groups]

    db['dups'] = dup_groups

    return db
    
def dup_removal_by_hash(db, db_type, dup_allow_dist, hash_type):
    #Assumption: You've run set_up_db_gropus previously
    #All this bullshit is to get around lists as items in pandas   
    dup_groups = db.dups.tolist()
    image_index = [x[0] for x in dup_groups]
    
    #Load in the hash_differences
    if db_type == 'user':
        hdiffs = compute_all_diffs('/Users/oisin-brogan/Downloads/moderated_photos/by_user/'
                               + str(db.user_id.values[0]) + '/', hash_type)
    elif db_type == 'recipe':
        hdiffs = compute_all_diffs('/Users/oisin-brogan/Downloads/step_photos2/by_recipe/'
                               + str(db.recipe_id.values[0]) + '/', hash_type)
    else:
        print("Invalid db_type!")
        return    
    hdiffs = hdiffs.dropna(how='all').dropna(how='all', axis=1)
    tmp_df = hdiffs.copy()
    #db might be pruned by previous rule, so we select out the subset
    tmp_df = tmp_df.loc[db.image_id, db.image_id] 
    #We're going to alter the df as we go, as lets for through an index
    index = tmp_df.index.tolist()
    for img in index:
        if img in tmp_df.index:
            row = tmp_df.loc[img]
            found_dups = row[row<dup_allow_dist].index
            found_dups = found_dups.difference([img]) #Don't remove the original photo
            #Add dups to the dup_group
            dup_groups[image_index.index(img)] = dup_groups[image_index.index(img)] + found_dups.tolist()
            tmp_df = tmp_df.drop(found_dups).drop(found_dups, axis=1)
    hdiffs = tmp_df.copy()
       
    db_pruned = db.copy()
    db_pruned = db_pruned.set_index('image_id').loc[hdiffs.index.values].reset_index()
    dup_groups = [dup_groups[image_index.index(img_id)] for img_id in db_pruned.image_id.tolist()]   
    db_pruned['dups'] =  dup_groups
    
    return db_pruned

def dup_removal_by_hash_timed(db, db_type, dup_allow_dist, max_time, hash_type):
    #Assumption: You've run set_up_db_gropus previously
    dup_groups = db.dups.tolist()
    image_index = [x[0] for x in dup_groups]
    
    #Load in hash differences
    if db_type == 'user':
        hdiffs = compute_all_diffs('/Users/oisin-brogan/Downloads/moderated_photos/by_user/'
                               + str(db.user_id.values[0]) + '/', hash_type)
    elif db_type == 'recipe':
        hdiffs = compute_all_diffs('/Users/oisin-brogan/Downloads/step_photos2/by_recipe/'
                               + str(db.recipe_id.values[0]) + '/', hash_type)
    else:
        print("Invalid db_type!")
        return
        
    hdiffs = hdiffs.dropna(how='all').dropna(how='all', axis=1)
    tmp_df = hdiffs.copy()
    #db might be pruned by previous rule, so we select out the subset
    tmp_df = tmp_df.loc[db.image_id, db.image_id] 
    chronolical = db.sort('taken_at').set_index('image_id').taken_at
    #We're going to alter the df as we go, as lets for through an index
    index = tmp_df.index.tolist()
    for img in index:
        if img in tmp_df.index:
            row = tmp_df.loc[img]
            time_diffs = chronolical - chronolical.loc[img]
            within_window = row[(time_diffs < max_time) & (time_diffs >= pd.Timedelta(0))]
            concurrent_dups = within_window[within_window<dup_allow_dist].index
            concurrent_dups = concurrent_dups.difference([img]) #Don't remove the original photo            
            #Add dups to dup_group
            relevant_dup_groups = [dup_groups[image_index.index(i)] for i in concurrent_dups]
            if relevant_dup_groups:
                relevant_dup_groups = reduce(lambda x,y: x+y, relevant_dup_groups)
                dup_groups[image_index.index(img)] = dup_groups[image_index.index(img)] + relevant_dup_groups
            tmp_df = tmp_df.drop(concurrent_dups).drop(concurrent_dups, axis=1)
            
    hdiffs = tmp_df.copy()
    db_pruned = db.set_index('image_id').loc[hdiffs.index.values].reset_index()
    dup_groups = [dup_groups[image_index.index(img_id)] for img_id in db_pruned.image_id.tolist()]
    db_pruned['dups'] =  dup_groups
    
    
    return db_pruned
    
def dup_removal_by_min_time(db, min_time):
    #Assumption: You've run set_up_db_gropus previously
#    dup_groups = db.dups.tolist()
#    image_index = [x[0] for x in dup_groups]
    
    chronolical = db.sort('taken_at')
    if chronolical.shape[0] < 3:
            return pd.DataFrame() #3's our minmum recipe steps
    
    time_diffs = chronolical.taken_at.diff()
    while time_diffs.min() < min_time: 
        #Add dups to the dup_group
        for idx in reversed(range(chronolical.shape[0])):
            if time_diffs.iloc[idx] < min_time:
                chronolical.loc[:,'dups'].iloc[idx-1] = chronolical.iloc[idx-1]['dups'] + chronolical.iloc[idx]['dups']
        #Drop photos taken too close in time
        chronolical = chronolical.drop(chronolical.index[time_diffs < min_time])
        
        if chronolical.shape[0] < 3:
            return pd.DataFrame() #3's our minmum recipe steps
         
        time_diffs = chronolical.taken_at.diff()
    
    db_pruned = chronolical.copy()
#    dup_groups = [dup_groups[image_index.index(img_id)] for img_id in db_pruned.image_id.tolist()]
#    db_pruned['dups'] =  dup_groups
    
    return db_pruned

#Convertion betweeb duplicate groups and the top photo handling
def suggestions_with_dup_groups_to_singles(suggestions):
    singles = []
    for suggestion in suggestions:
        singles.append([x[0] for x in suggestion])
    return singles
    
def singles_back_to_dup_groups(singles, user_suggestions):
    flat_list, single_index = [], []
    for suggestion in user_suggestions:
        for group in suggestion:
            flat_list.append(group)
            single_index.append(group[0])
    
    for i, single in enumerate(singles):
        for j, img_id in enumerate(single):
            singles[i][j] = flat_list[single_index.index(img_id)]

    return singles
    
def suggestions_with_dup_groups_to_flat(user_suggestions):
    flat_list = []
    for suggestion in user_suggestions:
        flat_suggestion = reduce(lambda x,y: x+y, suggestion)
        flat_list.append(flat_suggestion)

    return flat_list

#Merge similar suggestions
def merge_similar_suggestions(user_suggestions, allowed_overlap):
    singles = suggestions_with_dup_groups_to_singles(user_suggestions)
    
    sets = [set(suggestion) for suggestion in singles if suggestion]
    merged = 1
    while merged:
        merged = 0
        results = []
        while sets:
            common, rest = sets[0], sets[1:]
            sets = []
            for x in rest:
                if len(x.intersection(common)) < allowed_overlap:
                    sets.append(x)
                else:
                    merged = 1
                    common |= x
            results.append(common)
        sets = results
    singles = [list(s) for s in sets if s]
    suggestions = singles_back_to_dup_groups(singles, user_suggestions)
    return suggestions
    
#### Suggestion Rules ####

def three_similar_concurrent(db, db_type, max_allow_hash_diff, total_time, hash_type):
    if db.empty:
        return []
    chronolical = db.sort('taken_at')
    if db_type == 'user':
        hdiffs = compute_all_diffs('/Users/oisin-brogan/Downloads/moderated_photos/by_user/'
                               + str(db.user_id.values[0]) + '/', hash_type)
    elif db_type == 'recipe':
        hdiffs = compute_all_diffs('/Users/oisin-brogan/Downloads/step_photos2/by_recipe/'
                               + str(db.recipe_id.values[0]) + '/', hash_type)
    else:
        print("Invalid db_type!")
        return
        
    suggestions = []
    
    for time in chronolical.taken_at.values:
        time_diffs = chronolical.taken_at - time
        within_window = chronolical[(time_diffs < total_time) & 
                                    (time_diffs >= pd.Timedelta(minutes=0))]
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
        if relevent_hdiffs.shape[0] >= 3:
            possibility = relevent_hdiffs.columns.tolist()
            final_time = chronolical[chronolical.image_id == possibility[-1]].taken_at.values[0]
            suggestion_time = final_time - time
            #Check suggestion spans a minimum time
            if suggestion_time/pd.Timedelta(minutes=1) > 0:
                #Check if this possibility is a subset of any previous suggestion
                if sum([set(possibility) <= set(s) for s in suggestions]) == 0:
                    suggestions.append(possibility)

    #Convert to dup_groups
    db = db.set_index('image_id')
    for suggestion in suggestions:
        for i, image_id in enumerate(suggestion):
            suggestion[i] = db.loc[image_id, 'dups']
    
    return suggestions

    
def general_rule_applier(db, pre_processing, main_rule, post_processing, **kwargs):
    #Apply pre-processing
    if 'pre_args' in kwargs.keys():
        for f, args in zip(pre_processing, kwargs['pre_args']):
            db = f(db, *args)
            if db.empty:
                return []
    #Apply main
    suggestions = main_rule(db, *kwargs['main_args'])
    #Apply post-processing
    if 'post_args' in kwargs.keys():
        for f, args in zip(post_processing, kwargs['post_args']):
            suggestions = f(suggestions, *args)
    
    #Convert any dup groups to a flat_list for each evalualation
    #suggestions = suggestions_with_dup_groups_to_flat(suggestions)
    return suggestions
            
#### How do we decide we made a 'correct' suggestion? ####
# - all photos are subset of 1 recipe
# - X photos not in the recipe (X probably has to equal 1) (keep track of this)
# - Must be a certain % of recipe? (% ~= 75) <- interesting to see how this changes rating

def is_suggestion_recipe(suggestion, user_recipes, max_extra = 1, min_percentage = .75):
    """suggestion is a list of image ids making a suggestion given by the rules
    user_recipes is a list of lists of image ids, detailing all the recipes
    manually identitified in the user's photos"""
    #Bools to show if we ever meet the condidtions individually, but not in 
    #the same recipe
    best_extra_photos = False
    best_suff_cover = False
    
    flat_suggestion = reduce(lambda x,y: x+y, suggestion)
    singles = [x[0] for x in suggestion]
    
    for recipe in user_recipes:
        no_extra_photos = False
        suff_cover = False
    
        sf_matches = sum([i in recipe for i in flat_suggestion])
        ep_matches = sum([i in recipe for i in singles])
        extra_photos = len(suggestion) - ep_matches
        ex_ph_per = float(ep_matches) / len(suggestion)
        percentage = float(sf_matches) / len(recipe)
        if extra_photos <= max_extra:# or ex_ph_per < .1:
            no_extra_photos = True
            best_extra_photos = True
        if percentage >= min_percentage:
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

def best_cover(suggestion, user_recipes):
    """suggestion is a list of image ids making a suggestion given by the rules
    user_recipes is a list of lists of image ids, detailing all the recipes
    manually identitified in the user's photos"""    
    flat_suggestion = reduce(lambda x,y: x+y, suggestion)
    
    best_cover = 0
    
    for recipe in user_recipes:
        sf_matches = sum([i in recipe for i in flat_suggestion])
        percentage = float(sf_matches) / len(recipe)
        if percentage > best_cover:
            best_cover = percentage
        
    return best_cover

def eval_users_cover(suggestions, user_id, all_user_recipes, max_extra = 1, min_percentage = .75):
    user_recipes = all_user_recipes[user_id]
    if not user_recipes:
        #No recipes => all suggestions are false
        results = [0]*len(suggestions)
        return results
    results = []
    for suggestion in suggestions:
        results.append(best_cover(suggestion, user_recipes))
        
    return results