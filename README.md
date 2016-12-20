# Step Suggestions

In this project we're exploring to see if we can automatically detect a group of photos that are the steps to a recipe.
Once step photos are detected, we can suggest to the user to perhaps create a new recipe.
Or perhaps once they've started to create a recipe, to automatically suggest photos to add as steps.

## Initial approach

As a first pass, we're exploring using EXIF data and [similary hashes](https://github.com/cookpad/similar-images) to
identify step recipes.

Later itterations will almost certainly need some sort of machine learning technqiues.

## Methods and packages
- Use pypuzzle and imagehash to generate similarity hashes.
- Use exifread to read EXIF data. At the moment only use the datetime tag.
- Use Tkinter to create a GUI to allow user quick labelling of suggestions made by the system as correct or not.

## Data
- We use Cookpad's database of step photos as exisiting examples.
- We use moderator approved photos classified by Foodnet as our test set.
