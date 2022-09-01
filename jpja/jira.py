# loading the request and saving it for later
import requests
from requests.auth import HTTPBasicAuth
import json
import pickle 

# dates
import datetime
import dateutil.parser

# pretty printing and niceties
from pprint import pprint
from rich import print
from rich import inspect
from rich.progress import track
from time import sleep

# Jon
from classes import Issue
from functions import get_time_difference_from_strings
from functions import string_to_date

story_points_custom_field = "customfield_10026"
epic_link_custom_field = "customfield_10014"

""" works for reference
curl -D- \
   -u "USERNAME":PASSWORD \
   -X GET \
   -H "Content-Type: application/json" \
   "https://JIRA_URL/rest/api/2/search?jql=project=PROJECT1" -L
"""


def get_all_epics(auth, domain):

    try:
        with open('all_epics.obj', 'rb') as f:
            all_epics_dict = pickle.load(f)
    except IOError:
        print("File not accessible")

        jql_string = 'issuetype = Epic'

        all_epics_dict = {}

        # search
        search_url = domain + "/rest/api/2/search?jql=%s" % jql_string
        headers = {"Accept": "application/json"}

        # first, just get the number of issues in the result to verify
        search_url_first = search_url + "&maxResults=1"
        response = requests.request("GET", search_url_first, headers=headers, auth=auth)

        number_of_issues = response.json()['total']
        print("number of epics: %s" % response.json()['total'])

        # next, do the full query with max 50 issues per result page
        # I tried 200 once and it didn't work properly (only returned 100 results)
        # Tried again 2022-06-02. 100 results is the max.
        # same issue in load_issues
        number_of_results = 100
        x = 0
        while x < number_of_issues:
            print("x: %s" % x)
            search_url_this_page = search_url + "&startAt=%s&maxResults=%s" % (x, number_of_results)
            print(search_url_this_page)

            response = requests.request("GET", search_url_this_page, headers=headers, auth=auth)
            x += number_of_results
            print("x is: %s" % x)

            api_issue_count = 0   # counting the number of issues returned (should match number_of_results)
            for issue in response.json()['issues']:
                api_issue_count += 1
                #pprint(issue)
                #print("adding... %s %s" % (issue['key'], issue['fields']['summary']))
                all_epics_dict[issue['key']] = "Epic: " + issue['fields']['summary'] # added epic: for making the graph later
            print("api_issue_count: %s.  Should match %s." % (api_issue_count, number_of_results))

        # write this to a file
        filehandler = open("all_epics.obj", 'wb') 
        pickle.dump(all_epics_dict, filehandler)

    return all_epics_dict



def load_issues(auth, domain, JQL):
    # try to open the all_issues file to read the object
    # if it doesn't exist, get it from the Jira API
    try:
        with open('all_issues.obj', 'rb') as f:
            all_issues_list = pickle.load(f)
    except IOError:
        print("File not accessible")

        jql_string = JQL

        all_issues_list = []

        # search
        search_url = domain + "/rest/api/2/search?jql=%s" % jql_string
        print("search URL: %s" % search_url)
        headers = {"Accept": "application/json"}

        # first, just get the number of issues in the result to verify
        search_url_first = search_url + "&maxResults=1"
        response = requests.request("GET", search_url_first, headers=headers, auth=auth)


        number_of_issues = response.json()['total']
        
        print("number of issues: %s" % number_of_issues)

        # next, do the full query with max 100 issues per result page
        # I tried 200 once and it didn't work properly (only returned 100 results)
        # Tried again 2022-06-02. 100 results is the max
        # same issue in .get_all_epics
        number_of_results = 100
        x = 0

        import math
        # ceil() rounds up
        for i in track(range(math.ceil(number_of_issues/number_of_results)), description="Paginating API calls..."):
        # while x < number_of_issues:
            print("x: %s" % x)
            # "&startAt=%s&maxResults=%s"   ← original, then I added stuff to get the changelog
            search_url_this_page = search_url + "&startAt=%s&maxResults=%s" % (x, number_of_results)
            #search_url_this_page = search_url + "&startAt=%s&maxResults=%s&fields=summary,key,changelog,created,resolutiondate&expand=changelog" % (x, number_of_results)
            print(search_url_this_page)

            response = requests.request("GET", search_url_this_page, headers=headers, auth=auth)
            x += number_of_results

            api_issue_count = 0   # counting the number of issues returned (should match number_of_results)
            for issue in response.json()['issues']:
                api_issue_count += 1
                #print("adding... %s" % issue['key'])
                all_issues_list.append(issue)
            print("api_issue_count: %s.  Should match %s." % (api_issue_count, number_of_results))

        # write this to a file
        filehandler = open("all_issues.obj", 'wb') 
        pickle.dump(all_issues_list, filehandler)


    # print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))

    # for j in all_issues_list:
    #     print(j['key'])

    return all_issues_list


def get_issue_objects_list(everything, GET_IN_PROGRESS):

    issue_list = []
    issue_types_list = []
    priorities_list = []

    # create an instance of all issues in a list
    # for i in everything:
    for i in track(everything, description="Creating an instance of all issues in a list..."):

        # view the jira JSON response below
        # print(i)
        # exit()

        this_issue = Issue(issuetype = i['fields']['issuetype']['name'], \
        summary = i['fields']['summary'], \
        key = i['key'])
        this_issue.linked_issue_keys = [] # added to reset this list during iteration
        this_issue.add_date_created(string_to_date(i['fields']['created']).strftime("%Y-%m-%d"))
        if i['fields']['resolutiondate'] is None: # This deals with tickets with no resolution date
            this_issue.add_date_completed(datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            this_issue.add_date_completed(string_to_date(i['fields']['resolutiondate']).strftime("%Y-%m-%d"))
        this_issue.story_points = i['fields']['customfield_10026']
        this_issue.epic = i['fields'][epic_link_custom_field]
        this_issue.priority = i['fields']['priority']['name']
        if i['fields']['assignee'] is None:
            this_issue.assignee = "nobody"
        else:
            this_issue.assignee = i['fields']['assignee']['displayName']

        # hack to rename "No Priority"
        if this_issue.priority == "No Priority":
            this_issue.priority = "np"


        # parse the changelog to get the first date it was put in progress
        if GET_IN_PROGRESS:
            changelog = get_changelog(this_issue.key)
            if changelog != 0:
                #pprint(changelog['histories'])
                for j in changelog['histories']:
                    # pprint(j['created'])
                    # pprint(j['items'])
                    # pprint(j['items'][0]['toString'])
                    if j['items'][0]['toString'] == "In Progress":
                        print("In progress: %s" % string_to_date(j['created']).strftime("%Y-%m-%d"))
                        this_issue.add_date_in_progress(string_to_date(j['created']).strftime("%Y-%m-%d"))

        # makes a list of linked issue keys
        # some of them only have outward or inward links, hence the try/catch
        for l in i['fields']['issuelinks']:
            try:
                this_issue.linked_issue_keys.append(l['outwardIssue']['key'] + " " + l['outwardIssue']['fields']['summary'])
            except:
                pass
            try:
                this_issue.linked_issue_keys.append(l['inwardIssue']['key'] + " " + l['outwardIssue']['fields)']['summary'])
            except:
                pass


        issue_list.append(this_issue)

        # for color palette generation later
        if i['fields']['issuetype']['name'] not in issue_types_list:
            issue_types_list.append(i['fields']['issuetype']['name'])
        # for color palette generation later
        #print(i['fields']['priority']['name'] )
        if this_issue.priority not in priorities_list:
            priorities_list.append(this_issue.priority)

        # # everything below here needs to be done regardless
        # end = string_to_date(i['fields']['resolutiondate'])
        # start = string_to_date(i['fields']['created'])
        # difference = end - start

    return issue_list, issue_types_list, priorities_list


def get_changelog(jira_key):

    # auth = HTTPBasicAuth(USERNAME, TOKEN)
    # domain = DOMAIN

    headers = {"Accept": "application/json"}
    USERNAME = "JIRA_USERNAME"
    TOKEN = "JIRA_TOKEN"
    AUTH = HTTPBasicAuth(USERNAME, TOKEN)
    DOMAIN = "JIRA_URL" 

    domain = DOMAIN
    auth = AUTH

    url = domain + "/rest/api/2/issue/%s?expand=changelog" % jira_key

    try:
        response = requests.request("GET", url, headers=headers, auth=auth)
        return response.json()['changelog']
    except Exception as e:
        print(e)
        return 0



def get_story_points_custom_field_id():


    auth = HTTPBasicAuth(USERNAME, TOKEN)
    url = DOMAIN + "/rest/api/2/field"
    response = requests.request("GET", url, headers=headers, auth=auth)
    #print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))
    
    pprint(response.json())

    custom_field_id = ""
    for i in response.json():
        if i['name'] == "Story Points":
            custom_field_id = i['id']

    exit()

    return custom_field_id


if __name__ == '__main__':
    main()