#!/usr/bin/env python
# coding: utf-8

# # Create overview of Data Element usage (using launchpy)
# This notebook is used as example to show how the Launchpy module can help in creating an overview of where data elements are being used or which data elements are not being used at all within a Launch Property.
# 
# 
# **Warning - known edgecase:**
# 
# *This code assumes the full data element name is enclosed by either percentage characters or qoutes (single or double).*
# 
# *Therefore in the rare case a the data element name is set dynamically in code (e.g. `_satellite.getVar(some_prefix + some_name, events);`) the usage will not be detected!*

# ## Init
# 

# In[ ]:


import pandas as pd
import launchpy as lp
import re
from datetime import datetime


# This script expects a config file for Launchpy to be already available in `../config/admin.json`.
# If not, make sure to run the following code first and set the correct values after which you can move the file to the expected location.
# ```
# lp.createConfigFile()
# ```

# In[ ]:


lp.importConfigFile('../config/admin.json')
admin = lp.Admin()
my_cid = admin.getCompanyId()
my_cid


# ## Select property
# Retreive the list of properties within the account and select one.

# In[ ]:


my_properties = admin.getProperties(my_cid)
[my_property['attributes']['name'] for my_property in my_properties]


# In[ ]:


my_property_name = 'my demo property'
my_property = list(filter(lambda x: my_property_name == x ['attributes']['name'], my_properties))[0]
my_property = lp.Property(my_property)
my_property.name


# ## Fetch data elements, rules/rule components and extensions

# In[ ]:


data_elements = my_property.getDataElements()
rules = my_property.getRules()
rule_comps = my_property.getRuleComponents()
extensions = my_property.getExtensions()

print(f'Fetched:',
      f' - {len(data_elements)} data elements',
      f' - {len(rules)} rules consisting of {len(rule_comps)} rule components',
      f' - {len(extensions)} extensions.',
      sep='\n')


# In[ ]:


rule_actions = [rc for rc in rule_comps if '::actions::' in rc['attributes']['delegate_descriptor_id']]
rule_conditions = [rc for rc in rule_comps if '::conditions::' in rc['attributes']['delegate_descriptor_id']]
rule_events = [rc for rc in rule_comps if '::events::' in rc['attributes']['delegate_descriptor_id']]

print(f'Fetched:',
      f' - {len(rule_actions)} actions',
      f' - {len(rule_conditions)} conditions',
      f' - {len(rule_events)} events',
      sep='\n')

assert len(rule_comps) == len(rule_actions) + len(rule_conditions) + len(rule_events)


# ## Setup methods for matching and traversing

# In[ ]:


def find_occurrence_in_attributes(subject, pattern):
    '''Take the subject's attributes, cast it into a string and perform a regex search using pattern.'''
    try:
        attributes = lp.extractAttributes(subject)
        return re.search(pattern, str(attributes))
    except TypeError:
        print(f'Failed to get attributes and/or settings of subject {subject}')


def find_data_element_usage(data_elements=data_elements, rule_comps=rule_comps, extensions=extensions):
    '''Find usage of all ddata elements by checking each data elements attributes.'''
    results = dict()
    
    for data_element in data_elements:
        de_name = data_element['attributes']['name']
        pattern = re.escape(f'{de_name}')
        slashes = re.escape('\\\\')
        enclosing = f'(%|({slashes})?"|({slashes})?\')'
        pattern = f'{enclosing}{pattern}{enclosing}'
        
        # check data elements
        for subject in data_elements + rule_comps + extensions:
            if subject == data_element:
                # skip the subject itself
                continue
            if find_occurrence_in_attributes(subject, pattern):
                results.setdefault(de_name, []).append(subject)
                
    return results
    


# ## Run usage search

# In[ ]:


de_usage = find_data_element_usage()
de_usage


# ## Build easy to use output (DataFrame)

# In[ ]:


output_columns = ('data_element_name', 'usage_in_type', 'usage_in_name', 'usage_in_rule_name')
output_list = []

for de_name in de_usage.keys():
    usage = [
        {
            'data_element_name': de_name,
            'usage_in_type': subj['type'] if subj['type'] != 'rule_components' else 'rule_' + re.search(r'::(actions|conditions|events)::', subj['attributes']['delegate_descriptor_id']).group(1),
            'usage_in_name': subj['attributes']['name'] ,
            'usage_in_rule_name':  None if subj['type'] != 'rule_components' else subj['rule_name']
        } for subj in (de_usage[de_name] if de_name in de_usage else [])
    ]
    output_list += usage
#     for use in usage:
#         output_list.append((de_name,) + use)

# usage_df = pd.DataFrame(output_list, columns=output_columns)
usage_df = pd.DataFrame(output_list)
usage_df.set_index('data_element_name', inplace=True)
usage_df


# ... and make note of the Data elements that are not used anywhere.

# In[ ]:


not_used = [data_element['attributes']['name'] for data_element in data_elements] - de_usage.keys()
not_used_df = pd.DataFrame(not_used, columns=('data_element_name',))
not_used_df.set_index('data_element_name', inplace=True)
not_used_df


# ## Save to excel 
# Save to excel for easy sharing.

# In[ ]:


date = datetime.now().strftime('%Y_%m_%d_%H:%M:%S')
file = f'../output/data_element_usage_{date}.xlsx'

with pd.ExcelWriter(file) as writer:
    usage_df.to_excel(writer, sheet_name='data_elements_used')
    not_used_df.to_excel(writer, sheet_name='unused_data_elements')


# In[ ]:


get_ipython().system('ls ../output')


# In[ ]:




