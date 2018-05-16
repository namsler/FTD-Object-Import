#! importObjects.py
# This script will import host, network, and service objects from an ASA script
# For consistent results, use config files that do not have names.
# NOTE: a module to remove objects has been included. Be very careful with this module.
# It will delete ALL objects under that heading, including objects that are already in use by firewalls.
# To launch the script, be sure the the firewall config and the script are in the same folder.
# In powershell run the command "python importObjects.py"
# The script will prompt for the config name, IP of the FMC and the username and password.
# The script will then parse the config file and then import the specified objects into the FMC.
# It is recommended to run the script on a test FMC prior to running on the operational firewall
###################################################################################################

import sys, os, pprint, netaddr, openpyxl, re, requests, json, time
ASALines = []
names = []
ids = []
wb = openpyxl.Workbook('objects.xlsx')
j = 1

def main():
    importConfig()
    findNames()
    connect()
    collectCurrentIds()
    HostObjects()
    NetworkObjects()
    RangeObjects()
    URLObjects()
    ServiceObjects()

def importConfig():
    global ASALines
    global ASAConfigLines
    x = 'abcd'
    while x == 'abcd':
        FileName = input('Specify ASA Configuration file: ')
        if FileName not in os.listdir('.'):
            print('File not in current directory. Please specify a file in the current directory')
        else:       
            configFile = open(FileName)
            lines = []
            lineID = 0
            for line in configFile:
                line = line.replace('\n', '')
                ASALines.append(line)
            x = 1

def findNames():
    global names
    if ASALines == []:
        print('Config Not Loaded')
    for i in range(0,len(ASALines)):
        name = {}
        line = ASALines[i].split()
        if line != []:
            if line[0] == 'name':
                name['name'] = line[2]
                name['address'] =line[1]
                names.append(name)
    if names != []:
        print('Names were found in the configuration')
        x = 'start loop'
        while x == 'start loop':
            replaceQuestion = input('Do you want this script to replace the names with the specified values:  ')
            if replaceQuestion == 'no':
                x = 'stop'
            elif replaceQuestion == 'yes':
                replaceNames()
                x = 'stop'
            else:
                print("Please answer with 'yes' or 'no'")

def replaceNames():
    print('Replacing....')
    for i in range(0,len(names)):
        reg = re.compile(names[i]['name'])
        for m in range(0,len(ASALines)):
            x = 0
            line = ASALines[m].split()
            for j in range(0,len(line)):
                if line[0] != 'name':
                    b = reg.search(line[j])
                    if b != None:
                        line[j] = names[i]['address']
                        line = ' '.join(line)
                        x = 1
            if x == 1:
                ASALines[m] = line
    x = 'Start Loop'
    while x == 'Start Loop':
        question = input('Would you like to save this configuration as new file [yes | no]: ')
        if question == 'yes':
            fileName = input('Specify File Name: ')
            print('Saving....')
            file = open(fileName, 'w')
            ASARevisedConfig = []
            for i in range(0,len(ASALines)):
                if ASALines[i].startswith('name') != True:
                    ASARevisedConfig.append(ASALines[i])
            for line in ASARevisedConfig:
                file.write(line +'\n')
            x = 'stop'
        elif question == 'no':
            x = 'stop'
        else:
            print('Please answer with yes or no')

def connect():
    global headers
    global server
    serverIP = input("Server IP Adress:  ")
    server = ("https://%s" % serverIP)
    username = input("Username:   ")
    password = input("Password: ")
    r = None
    headers = {'Content-Type': 'application/json'}
    api_auth_path = "/api/fmc_platform/v1/auth/generatetoken"
    auth_url = server + api_auth_path
    r = requests.post(auth_url, headers=headers, auth=requests.auth.HTTPBasicAuth(username,password), verify=False)
    auth_headers = r.headers
    auth_token = auth_headers.get('X-auth-access-token', default=None)
    if auth_token == None:
        print("Connection Failed")
    headers['X-auth-access-token']=auth_token           

def collectCurrentIds():
    global headers, server, ids
    if headers == {}:
        print("FMC not connected")
        return
    apiCategories = ['networkgroups','portobjectgroups','urlgroups' 'vlangrouptags', 'hosts', 'icmpv4objects','icmpv6objecs', 'networks','protocolportobjects', 'ranges', 'urls',  'vlantags']
    newCategory = ""
    for api in apiCategories:
        api_path = ('/api/fmc_config/v1/domain/e276abec-e0f2-11e3-8169-6d9ed49b625f/object/%s?limit=1000' % api)
        url = server + api_path
        r = requests.get(url, headers=headers, verify=False)
        resp = r.text
        json_resp = json.loads(resp)
        if 'items' in (json_resp.keys()):
            item = json_resp['items']
            numItems = len(item)
            for i in range(0,numItems):
                ids.append(item[i]['id'])             

def HostObjects():
    if ASALines == []:
        print('Config Not Loaded')
    for i in range(0,len(ASALines)):
        Line = {}
        if 'object network' in ASALines[i]:
            Line2 = ASALines[i+1]
            if 'host' in Line2:
                name = ASALines[i].split()[2]
                descript = description(Line2)
                address = Line2.split()[1]
                put_data = {"name": name, "value": address, "description": descript}
                create_objects(put_data, 'hosts')
                #remove_objects()
    print(ids)

                
def NetworkObjects():
    if ASALines == []:
        print('Config Not Loaded')
    for i in range(0,len(ASALines)):
        Line = {}
        if 'object network' in ASALines[i]:
            Line2 = ASALines[i+1]
            if 'subnet' in Line2:
                name = ASALines[i].split()[2]
                descript = description(Line2)
                subnet = GetCIDR(Line2)
                put_data = {"name": name, "value": subnet, "description": descript}
                create_objects(put_data, 'networks')
                #remove_objects()

def RangeObjects():
    if ASALines == []:
        print('Config Not Loaded')
    for i in range(0,len(ASALines)):
        Line = {}
        if 'object network' in ASALines[i]:
            Line2 = ASALines[i+1]
            if 'range' in Line2:
                name = ASALines[i].split()[2]
                descript = description(Line2)
                startAddr = Line2.split()[1]
                endAddr = Line2.split()[2]
                rangeObj = startAddr + "-" + endAddr          
                put_data = {"name": name, "value": rangeObj, "description": descript}
                create_objects(put_data, 'ranges')
                #remove_objects()
           
def URLObjects():
    if ASALines == []:
        print('Config Not Loaded')
    for i in range(0,len(ASALines)):
        Line = {}
        if 'object network' in ASALines[i]:
            Line2 = ASALines[i+1]
            if 'fqdn' in Line2:
                name = ASALines[i].split()[2]
                descript = description(Line2)
                fqdn = Line2.split()[2]
                put_data = {"name": name, "url": fqdn, "description": descript}
                create_objects(put_data, 'urls')
                #remove_objects()
                
def ServiceObjects():
    if ASALines == []:
        print('Config Not Loaded')
    for i in range(0,len(ASALines)):
        Line = {}
        if 'object service' in ASALines[i]:
            Line2 = ASALines[i+1]
            name = ASALines[i].split()[2]
            descript = description(Line2)
            protocol = Line2.split()[1]
            operator = Line2.split()[3]
            port = FindPorts(Line2, operator, 'object')
            put_data = {"name": name, "protocol": protocol, "description": descript, "port": port}
            create_objects(put_data, 'protocolportobjects')
            #remove_objects()
    
def create_objects(put_data,variable):
    global j
    response = None
    global headers
    global server
    global ids
    if headers == {}:
        print("FMC not connected")
        return
    obj_url = server + ("/api/fmc_config/v1/domain/e276abec-e0f2-11e3-8169-6d9ed49b625f/object/%s" % variable)
    response = requests.post(obj_url,headers=headers,data=json.dumps(put_data),verify = False)
    j = j+1
    if j > 100:
        print("1 minute sleep due to system max requests per minute")
        time.sleep(60)
        j = 1
    if response.status_code != 201:
        print(response.text)
    else:
        json_resp = json.loads(response.text)
        ids.append(json_resp['id'])



def remove_objects():
    global headers, server
    if headers == {}:
        print("FMC not connected")
        return
    ids =[]
    apiCategories = ['protocolportobjects']
    #apiCategories = ['networkgroups','portobjectgroups','urlgroups' 'vlangrouptags', 'hosts', 'icmpv4objects','icmpv6objecs', 'networks','protocolportobjects', 'ranges', 'urls',  'vlantags']
    for api in apiCategories:
        api_path = ('/api/fmc_config/v1/domain/e276abec-e0f2-11e3-8169-6d9ed49b625f/object/%s?limit=1000' % api)
        url = server + api_path
        r = requests.get(url, headers=headers, verify=False)
        resp = r.text
        json_resp = json.loads(resp)
        item = json_resp['items']
        j= 1
        numItems = len(item)
        for i in range(0,numItems):
            ids.append(item[i]['id'])
        for item in ids:
            api_path = ('/api/fmc_config/v1/domain/e276abec-e0f2-11e3-8169-6d9ed49b625f/object/%s/%s' % (api,item))
            url = server + api_path
            r = requests.delete(url, headers=headers, verify=False)
            print(r.status_code,r.text)
            j = j + 1
            if j > 100:
                print("1 minute sleep due to system max requests per minute")
                time.sleep(60)
                j = 1

                             
####TOOLS###
                
def description(Line2):
    description = ''
    if 'description' in Line2:
        description = (Line2[13:])
    return description

def GetCIDR(Line2): 
    subnet = Line2.split()[1]
    netmask = Line2.split()[2]
    bits = str(netaddr.IPAddress(netmask).netmask_bits())
    CIDR = subnet + "/" + bits
    return CIDR

def FindPorts(Line2, operator, type):
    if type == 'object':
        i = 4
    elif type == 'group':
        i = 3
    elif type == 'port-object':
        i = 2
    if operator == 'eq':
        port = Line2.split()[i]
    elif operator == 'gt':
        port = str(int(Line2.split()[i]) + 1) + '-65535'
    elif operator == 'lt':
        port = '1-' + str(int(Line2.split()[i]) - 1)
    elif operator == 'range':
        port = Line2.split()[i] + '-' + Line2.split()[i+1]
    return port


main()