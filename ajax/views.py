import os

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect, HttpResponse
from django.template.loader import render_to_string
from django.conf import settings

from common.lib.WistarException import WistarException
import common.lib.wistarUtils as wu
import common.lib.libvirtUtils as lu
import common.lib.junosUtils as ju
import common.lib.linuxUtils as lxu
import common.lib.consoleUtils as cu
import common.lib.osUtils as ou
import common.lib.vboxUtils as vu
from images.models import Image
from templates.models import ConfigTemplate
from topologies.models import Topology
from topologies.models import ConfigSet
from topologies.models import Config


# import logging
import time
import json

# FIXME = debug should be a global setting
debug = True


def index(request):
    return HttpResponseRedirect('/topologies/')


def manage_hypervisor(request):
    return render(request, 'ajax/manageHypervisor.html')


def viewDomain(request, domain_id):
    domain = lu.get_domain_by_uuid(domain_id)
    return render(request, 'ajax/viewDomain.html', {'domain': domain, 'xml': domain.XMLDesc(0)})


def viewNetwork(request, network_name):
    network = lu.get_network_by_name(network_name)
    return render(request, 'ajax/viewNetwork.html', {'network': network, 'xml': network.XMLDesc(0)})


@csrf_exempt
def preconfigJunosDomain(request):
    response_data = { "result": True}
    required_fields = {'domain', 'password', 'ip', 'mgmtInterface'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    domain = request.POST['domain']
    password = request.POST['password']
    ip = request.POST['ip']
    mgmtInterface = request.POST['mgmtInterface']
    
    print "Configuring domain:" + str(domain)
    try:

        # let's see if we need to kill any webConsole sessions first
        webConsoleDict = request.session.get("webConsoleDict")
        if webConsoleDict is not None:
            if webConsoleDict.has_key(domain):
                wsConfig = webConsoleDict[domain]
                wsPort = wsConfig["wsPort"]
                server = request.get_host().split(":")[0]
                wu.killWebSocket(server, wsPort)

        # FIXME - there is a bug somewhere that this can be blank ?
        if mgmtInterface == "":
            mgmtInterface = "em0"
        elif mgmtInterface == "em0":
            if not ou.checkIsLinux():
                mgmtInterface = "fxp0"
        
        response_data["result"] = cu.preconfig_junos_domain(domain, password, ip, mgmtInterface)
        print str(response_data)
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    except WistarException as we:
        print we
        response_data["result"] = False
        response_data["message"] = str(we)
        return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def preconfigLinuxDomain(request):
    response_data = {"result": True}
    required_fields = {'domain', 'hostname', 'password', 'ip', 'mgmtInterface'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    domain = request.POST['domain']
    password = request.POST['password']
    ip = request.POST['ip']
    mgmtInterface = request.POST['mgmtInterface']
    hostname = request.POST['hostname']

    print "Configuring linux domain:" + str(domain)
    try:
        response_data["result"] = cu.preconfig_linux_domain(domain, hostname, password, ip, mgmtInterface)
        print str(response_data)
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    except WistarException as we:
        print we
        response_data["result"] = False
        response_data["message"] = str(we)
        return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def preconfigFirefly(request):
    response_data = {"result": True}
    required_fields = {'domain', 'password', 'mgmtInterface'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    domain = request.POST['domain']
    password = request.POST['password']
    mgmtInterface = request.POST['mgmtInterface']
    ip = request.POST['ip']
    
    try:
        # let's see if we need to kill any webConsole sessions first
        webConsoleDict = request.session.get("webConsoleDict")
        if webConsoleDict is not None:
            if webConsoleDict.has_key(domain):
                wsConfig = webConsoleDict[domain]
                wsPort = wsConfig["wsPort"]
                server = request.get_host().split(":")[0]
                wu.killWebSocket(server, wsPort)

        print "Configuring management Access"
        if cu.preconfig_junos_domain(domain, password, ip, mgmtInterface):
            print "Configuring Firefly management zones:" + str(domain)
            time.sleep(3)
            response_data["result"] = cu.preconfig_firefly(domain, password, mgmtInterface)
        else:
            response_data["result"] = False
            response_data["message"] = "Could not configure Firefly access"

        return HttpResponse(json.dumps(response_data), content_type="application/json")

    except WistarException as we:
        print we
        response_data["result"] = False
        response_data["message"] = str(we)
        return HttpResponse(json.dumps(response_data), content_type="application/json")

@csrf_exempt
def configJunosInterfaces(request):
    response_data = {"result": True}
    required_fields = {'password', 'ip'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    ip = request.POST['ip']
    password = request.POST['password']
    print "Configuring interfaces for " + str(ip)
    try:
        response_data["result"] = ju.config_junos_interfaces(ip, password)
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    except WistarException as we:
        print we
        response_data["result"] = False
        response_data["message"] = str(we)
        return HttpResponse(json.dumps(response_data), content_type="application/json")
   
@csrf_exempt
def executeCli(request):
    response_data = {"result": True}
    required_fields = {'ip', 'pw', 'cli'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    ip = request.POST['ip']
    pw = request.POST['pw']
    cli = request.POST['cli']

    result = ju.execute_cli(ip, pw, cli)
    if result is None:
        response_data["result"] = False
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else: 

        response_data["output"] = result 
        return HttpResponse(json.dumps(response_data), content_type="application/json")

@csrf_exempt
def executeLinuxCli(request):
    response_data = {"result": True}
    required_fields = {'ip', 'pw', 'cli'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    ip = request.POST['ip']
    pw = request.POST['pw']
    cli = request.POST['cli']

    result = lxu.executeCli(ip, "root", pw, cli)
    if result is None:
        response_data["result"] = False
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else: 

        response_data["output"] = result 
        return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def getJunosStartupState(request):
    response_data = {"result": True}
    required_fields = {'name'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    name = request.POST['name']
    response_data["result"] = cu.is_junos_device_at_prompt(name)
    return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def getLinuxStartupState(request):
    response_data = {"result": True}
    required_fields = {'name'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    name = request.POST['name']
    response_data["result"] = cu.is_linux_device_at_prompt(name)
    return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def getJunosConfig(request):
    response_data = {"result": True}
    required_fields = {'ip', 'password'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    ip = request.POST['ip']
    password = request.POST['password']
    print "Getting Config for " + str(ip)
    try:
        xml = ju.get_config(ip, password)
        print xml

        return HttpResponse(json.dumps(response_data), content_type="application/json")
    except WistarException as we:
        print we
        response_data["result"] = False
        response_data["message"] = str(we)
        return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def getConfigTemplates(request):
    required_fields = {'ip'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    template_list = ConfigTemplate.objects.all().order_by('modified')
    
    ip = request.POST['ip']
    context = {'template_list': template_list, 'ip': ip}
    return render(request, 'ajax/configTemplates.html', context)


@csrf_exempt
def syncLinkData(request):
    response_data = {"result": True}
    required_fields = {'sourceIp', 'sourceType', 'targetIp', 'targetType', 'sourcePortIp', 'targetPortIp',
                       'sourceIface', 'targetIface', 'sourcePw', 'targetPw', 'json', 'topologyId'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})
    
    sourceIp = request.POST['sourceIp']
    sourceType = request.POST['sourceType']
    targetIp = request.POST['targetIp']
    targetType = request.POST['targetType']
    sourcePortIp = request.POST['sourcePortIp']
    targetPortIp = request.POST['targetPortIp']
    sourceIface = request.POST['sourceIface']
    targetIface = request.POST['targetIface']
    sourcePw = request.POST['sourcePw']
    targetPw = request.POST['targetPw']
    jsonData = request.POST['json']
    topologyId = request.POST['topologyId']

    try:
        if sourceIp != "0.0.0.0":
            print "Configuring interfaces for " + str(sourceIp)
            if sourceType == "linux":
                sourceResults = lxu.setInterfaceIpAddress(sourceIp, "root", sourcePw, sourceIface, sourcePortIp)
            else:
                sourceResults = ju.set_interface_ip_address(sourceIp, sourcePw, sourceIface, sourcePortIp)

            if sourceResults is False:
                raise WistarException("Couldn't set ip address on source VM")
        
        if targetIp != "0.0.0.0":
            if targetType == "linux":
                targetResults = lxu.setInterfaceIpAddress(targetIp, "root", targetPw, targetIface, targetPortIp)
            else:
                targetResults = ju.set_interface_ip_address(targetIp, targetPw, targetIface, targetPortIp)

            if targetResults is False:
                raise WistarException("Couldn't set ip address on target VM")

        print "saving sync data on topology json as well"
        topo = Topology.objects.get(pk=topologyId)
        topo.json = jsonData
        topo.save()

        response_data["result"] = "Success"
        print str(response_data)
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    except WistarException as we:
        print we
        response_data["result"] = False
        response_data["message"] = str(we)
        return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def startTopology(request):
    response_data = {"result": True}
    required_fields = {'topologyId'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})
    
    topologyId = request.POST['topologyId']

    if topologyId == "":
        print "Found a blank topoId, returning full hypervisor status"
        response_data["result"] = False
        response_data["message"] = "Blank Topology Id found"
        return HttpResponse(json.dumps(response_data), content_type="application/json")

    domain_list = lu.get_domains_for_topology("t" + topologyId + "_")
    network_list = []

    if ou.checkIsLinux():
        network_list = lu.get_networks_for_topology("t" + topologyId + "_")

    for network in network_list:
        print "Starting network: " + network["name"]
        if lu.start_network(network["name"]):
            time.sleep(1)
        else:
            response_data["result"] = False
            response_data["message"] = "Could not start network: " + network["name"]
            return HttpResponse(json.dumps(response_data), content_type="application/json")

    num_domains = len(domain_list)
    iter_counter = 1
    for domain in domain_list:
        print "Starting domain " + domain["name"]
        if lu.start_domain(domain["uuid"]):
            if iter_counter < num_domains:
                time.sleep(180)
            iter_counter += 1
        else:
            response_data["result"] = False
            response_data["message"] = "Could not start domain: " + domain["name"]
            return HttpResponse(json.dumps(response_data), content_type="application/json")
    
    time.sleep(5)
    print "All domains started"
    return refreshDeploymentStatus(request)

   
@csrf_exempt
def refreshDeploymentStatus(request):
    response_data = {"result": True}
    required_fields = {'topologyId'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})
    
    topologyId = request.POST['topologyId']


    if topologyId == "":
        print "Found a blank topoId, returing full hypervisor status"
        return refreshHypervisorStatus(request)

    domain_list = lu.get_domains_for_topology("t" + topologyId + "_")
    network_list = []
    isLinux = False
    if ou.checkIsLinux():
        isLinux = True
        network_list = lu.get_networks_for_topology("t" + topologyId + "_")

    context = {'domain_list': domain_list, 'network_list': network_list, 'topologyId': topologyId, 'isLinux': isLinux}
    return render(request, 'ajax/deploymentStatus.html', context)


@csrf_exempt
def refreshHostLoad(request):
    (one, five, ten) = os.getloadavg()
    load = {'one': one, 'five': five, 'ten': ten}
    context = {'load': load}
    return render(request, 'ajax/hostLoad.html', context)


@csrf_exempt
def refreshHypervisorStatus(request):
    domains = lu.list_domains()
    if ou.checkIsLinux():
        networks = lu.list_networks()
    else:
        networks = []

    context = {'domain_list': domains, 'network_list': networks}
    return render(request, 'ajax/deploymentStatus.html', context)


@csrf_exempt
def manageDomain(request):

    required_fields = {'domainId', 'action', 'topologyId'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    domainId = request.POST['domainId'] 
    action = request.POST['action'] 


    if action == "start": 
        if lu.start_domain(domainId):
            return refreshDeploymentStatus(request)
        else:
            return render(request, 'ajax/ajaxError.html', {'error': "Could not start domain!"})

    elif action == "stop":
        if lu.stop_domain(domainId):
            return refreshDeploymentStatus(request)
        else:
            return render(request, 'ajax/ajaxError.html', {'error': "Could not stop domain!"})
    
    elif action == "suspend":
        if lu.suspend_domain(domainId):
            return refreshDeploymentStatus(request)
        else:
            return render(request, 'ajax/ajaxError.html', {'error': "Could not suspend domain!"})

    elif action == "undefine":
        sourceFile = lu.get_image_for_domain(domainId)
        if lu.undefine_domain(domainId):
            if sourceFile is not None:
                ou.removeInstance(sourceFile)
            return refreshDeploymentStatus(request)
        else:
            return render(request, 'ajax/ajaxError.html', {'error': "Could not stop domain!"})
    else:
            return render(request, 'ajax/ajaxError.html', {'error': "Unknown Parameters in POST!"})


@csrf_exempt
def manageNetwork(request):

    required_fields = {'networkName', 'action', 'topologyId'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    networkName = request.POST['networkName'] 
    action = request.POST['action']

    if action == "start": 
        if lu.start_network(networkName):
            return refreshDeploymentStatus(request)
        else:
            return render(request, 'ajax/ajaxError.html', {'error': "Could not start network!"})
    elif action == "stop":
        if lu.stop_network(networkName):
            return refreshDeploymentStatus(request)
        else:
            return render(request, 'ajax/ajaxError.html', {'error': "Could not stop network!"})

    elif action == "undefine":
        if lu.undefine_network(networkName):
            return refreshDeploymentStatus(request)
        else:
            return render(request, 'ajax/ajaxError.html', {'error': "Could not stop domain!"})
    else:
            return render(request, 'ajax/ajaxError.html', {'error': "Unknown Parameters in POST!"})


@csrf_exempt
def applyConfigTemplate(request):
    print "Pushing Config Template"
    response_data = {"result": True}

    required_fields = {'id', 'ip', 'password'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    config_template_id = request.POST['id'] 
    ip = request.POST['ip'] 
    password = request.POST['password']

    configTemplate = ConfigTemplate.objects.get(pk=config_template_id)
    template = configTemplate.template
    cleaned_template = template.replace('\r\n', '\n')
    print cleaned_template
    if ju.push_config(cleaned_template, ip, password):
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        response_data["result"] = False
        response_data["message"] = "Could not apply config template"
        return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def pushConfigSet(request):
    print "Pushing ConfigSet"
    response_data = {"result": True}

    required_fields = {'id'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    configSetId = request.POST['id'] 

    print "csid is " + configSetId

    cs = ConfigSet.objects.get(pk=configSetId)

    print "Got cs"
    topo = cs.topology

    configs = Config.objects.filter(configSet=cs)

    for config in configs:
        print config.ip
        try:
            ju.push_config_string(config.deviceConfig, config.ip, config.password)
        except Exception as e:
            print "Could not reload config on " + str(config.ip)
            response_data["message"] = response_data["message"] + " Error pushing to " + str(config.ip)
            print e

    return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def deleteConfigSet(request):
    print "Deleting ConfigSet"
    response_data = {"result": True}

    required_fields = {'id'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    configSetId = request.POST['id']
    cs = ConfigSet.objects.get(pk=configSetId)
    cs.delete()
    
    return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def multiCloneTopology(request):
    response_data = {"result": True}
    required_fields = {'clones', 'topologyId'}
    if not required_fields.issubset(request.POST):

        response_data["message"] = "Invalid Parameters in Post"
        return HttpResponse(json.dumps(response_data), content_type="application/json")

    topo_id = request.POST["topologyId"]
    num_clones = request.POST["clones"]

    print num_clones

    topo = Topology.objects.get(pk=topo_id)
    orig_name = topo.name
    json_data = topo.json
    i = 0
    while i < int(num_clones):
        print "index:" + str(i)
        print "goal: " + str(num_clones)
        new_topo = topo
        new_topo.name = orig_name + " " + str(i + 1).zfill(2)
        new_topo.json = wu.cloneTopology(json_data)
        json_data = new_topo.json
        new_topo.id = None
        new_topo.save()
        i += 1

    return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def deployTopology(request):

    if not request.POST.has_key('topologyId'):
        return render(request, 'ajax/ajaxError.html', {'error': "No Topology Id in request"})
    
    topologyId = request.POST['topologyId']
    topo = {}
    try:
        topo = Topology.objects.get(pk=topologyId)
    except Exception as ex:
        print ex
        return render(request, 'ajax/ajaxError.html', {'error': "Topology not found!"})

    # let's parse the json and convert to simple lists and dicts
    config = wu.loadJson(topo.json, topologyId)
   
    try: 
        # FIXME - should this be pushed into another module?
        inlineDeployTopology(config)
    except Exception as e:
        return render(request, 'ajax/ajaxError.html', {'error': str(e)})

    domain_list = lu.get_domains_for_topology("t" + topologyId + "_")
    network_list = []
        
    if ou.checkIsLinux():
        network_list = lu.get_networks_for_topology("t" + topologyId + "_")
    context = {'domain_list': domain_list, 'network_list': network_list, 'isLinux': True, 'topologyId': topologyId}
    return render(request, 'ajax/deploymentStatus.html', context)


@csrf_exempt
def inlineDeployTopology(config):
    # only create networks on Linux/KVM
    print "Checking if we should create networks first!"
    if ou.checkIsLinux():
        for network in config["networks"]:
            try:
                if not lu.network_exists(network["name"]):
                    if debug:
                        print "Rendering networkXml for: " + network["name"]
                    networkXml = render_to_string("ajax/kvm/network.xml", {'network': network})
                    print networkXml
                    n = lu.define_network_from_xml(networkXml)
                    if n is False:
                        raise Exception("Error defning network: " + network["name"])

                print "Starting network"
                lu.start_network(network["name"])
            except Exception as e:
                raise Exception(str(e))

    # are we on linux? are we on Ubuntu linux? set kvm emulator accordingly
    vm_env = {}
    vm_env["emulator"] = "/usr/libexec/qemu-kvm"
    vm_env["pcType"] = "rhel6.5.0"
    if ou.checkIsLinux() and ou.checkIsUbuntu():
        vm_env["emulator"] = "/usr/bin/kvm-spice"
        vm_env["pcType"] = "pc"

    # by default, we use kvm as the hypervisor
    domainXmlPath = "ajax/kvm/"
    if not ou.checkIsLinux():
        # if we're not on Linux, then let's try to use vbox instead
        domainXmlPath = "ajax/vbox/" 

    for device in config["devices"]:
        try:
            if not lu.domain_exists(device["name"]):
                if debug:
                    print "Rendering deviceXml for: " + device["name"]

                image = Image.objects.get(pk=device["imageId"])

                # fixme - simplify this logic to return just the deviceXml based on
                # image.type and host os type (ou.checkIsLinux)
                imageBasePath = settings.MEDIA_ROOT + "/" + image.filePath.url
                instancePath = ou.getInstancePathFromImage(imageBasePath, device["name"])

                print "rendering xml for image type: " + str(image.type)
                if image.type == "junos_firefly":
                    print "Using firefly definition"
                    deviceXml = render_to_string(domainXmlPath + "domain_firefly.xml", {'device': device, 'instancePath': instancePath, 'vm_env': vm_env})
                else:
                    cloud_init_path = None
                    if image.type == "linux":
                        # grab the last interface
                        mgmt_iface = device["interfaces"][-1]["name"]
                        # this will come back to haunt me one day. Assume /24 for mgmt network is sprinkled everywhere!
                        mgmt_ip_addr = device["ip"] + "/24"
                        # domain_name, host_name, mgmt_ip, mgmt_interface
                        cloud_init_path = ou.create_cloud_init_img(device["name"], device["label"], mgmt_ip_addr, mgmt_iface)

                    deviceXml = render_to_string(domainXmlPath + "domain.xml", {'device': device, 'instancePath': instancePath, 'vm_env': vm_env, 'cloud_init_path': cloud_init_path})

                if debug:
                    print "Checking that image instance exists at " + str(instancePath)

                if ou.checkImageInstance(imageBasePath, device["name"]):
                    print "Image Instance already exists"
                else:
                    print "Image Instance does not exist"
                    if ou.createThinProvisionInstance(imageBasePath, device["name"]):
                        print "Successfully created instance"
                    else:
                        raise Exception("Could not create image instance for image: " + imageBasePath)

                if debug:
                    print "Defining domain"
                    print deviceXml

                d = lu.define_domain_from_xml(deviceXml)
                if d is False:
                    raise Exception("Error defining instance: " + device["name"])

            if not ou.checkIsLinux():
                # perform some special hacks for vbox
                dev_mgmt_ifaces = device["managementInterfaces"]
                mgmt_ip_addr = str(dev_mgmt_ifaces[0]["ip"])
                vu.preconfigureVMX(device["name"], mgmt_ip_addr)

        except Exception as ex:
            raise Exception(str(ex))


@csrf_exempt
def launchWebConsole(request):
    print "Let's launch a console!"

    required_fields = {'domain'}
    if not required_fields.issubset(request.POST):
        return render(request, 'ajax/ajaxError.html', {'error': "Invalid Parameters in POST"})

    response_data = {"result": True}
    domain = request.POST["domain"]
    print "Got domain of: " + domain
    # this keeps a list of used ports around for us
    webConsoleDict = request.session.get("webConsoleDict")

    # server = request.META["SERVER_NAME"]
    server = request.get_host().split(":")[0]

    print webConsoleDict
    if webConsoleDict is None:
        print "no previous webConsoles Found!"
        webConsoleDict = {}
        request.session["webConsoleDict"] = webConsoleDict

    print "OK, do we have this domain?"
    if domain in webConsoleDict:
        wsConfig = webConsoleDict[domain]
        wsPort = wsConfig["wsPort"]
        vncPort = wsConfig["vncPort"]

        if wu.checkWebSocket(server, wsPort):
            print "This WebSocket is already running"

            response_data["message"] = "already running on port: " + wsPort
            response_data["port"] = wsPort
            return HttpResponse(json.dumps(response_data), content_type="application/json")
        else:
            pid = wu.launchWebSocket(wsPort, vncPort, server)
            if pid is not None:
                wsConfig["pid"] = pid

                response_data["message"] = "started WebConsole on port: " + wsPort
                response_data["port"] = wsPort
                return HttpResponse(json.dumps(response_data), content_type="application/json")
            else:
                response_data["result"] = False
                response_data["message"] = "Could not start webConsole"
                return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        print "nope"
        # start the ws ports at 6900
        wsPort = len(webConsoleDict.keys()) + 6900

        print "using wsPort of " + str(wsPort)
        # get the domain from the hypervisor
        d = lu.get_domain_by_name(domain)
        # now grab the configured vncport
        vncPort = lu.get_domain_vnc_port(d)

        print "Got VNC port " + str(vncPort)
        pid = wu.launchWebSocket(wsPort, vncPort, server)

        if pid is None:
            print "oh no"
            response_data["result"] = False
            response_data["message"] = "Could not start webConsole"
            print "returning"
            return HttpResponse(json.dumps(response_data), content_type="application/json")

        print "Launched with pid " + str(pid)
        wcConfig = {}
        wcConfig["pid"] = str(pid)
        wcConfig["vncPort"] = str(vncPort)
        wcConfig["wsPort"] = str(wsPort)
      
        webConsoleDict[domain] = wcConfig 
        request.session["webConsoleDict"] = webConsoleDict

        response_data["message"] = "started WebConsole on port: " + str(wsPort)
        response_data["port"] = wsPort
        return HttpResponse(json.dumps(response_data), content_type="application/json")