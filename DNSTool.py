#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, subprocess
import argparse, ipaddress
import platform
sst = platform.system()

parser = argparse.ArgumentParser(description='DNS Resolve Tool')
parser.add_argument('-r', '--reverse', action='store_true', help='Reverse DNS resolution, or default ro forward resolution')
parser.add_argument('-i', '--input', required=True, help='Input ip/host list file')
parser.add_argument('-o', '--output', default='json', help='default result.json')
parser.add_argument('-f', '--function', default='dig', choices=['nslookup', 'host', 'dig', 'socket'], help='which function to use, default dig')
parser.add_argument('-s', '--server', default='8.8.8.8', help='DNSServer')

args = parser.parse_args()

# print (args.output)
validFileType = ['.json','.xml','.txt','.csv']
if args.output in validFileType or '.'+args.output in validFileType:
    outputFileName, outputFileType = 'result','.'+args.output
else:
    outputFileName, outputFileType = os.path.splitext(args.output)
    if outputFileType not in validFileType:
        print('[*] Filetype '+outputFileType+' not support, set to json :(')
        outputFileName, outputFileType = outputFileName,'.json'
        
outputFile = outputFileName + outputFileType

# print(outputFileName, outputFileType)
choices=['.xml', '.json', '.csv', '.txt']
if outputFileType not in choices:
    print('Invalid file type, only support: '+(', '.join(choices)).replace('.',''))
    exit(0)

print('reverse:', args.reverse)
print('input filename:', args.input)
print('output filename:', outputFile)
print('function:', args.function)
print('DNSServer:', args.server)

if not args.reverse and args.function == 'socket':
    print('[*] The socket method doesn\'t support forward DNS resolution now :( ')
    exit(0)
    
if args.reverse and 'host' in args.input.split('.') or\
   not args.reverse and 'ip' in args.input.split('.'):
    print('[*] Are your sure you input the right file?')

WinNotSupport = ['dig','host']
LinuxNotSupport = []
if (sst == 'Windows' and args.function in WinNotSupport) or \
    sst == 'Linux' and args.function in LinuxNotSupport:
    print('[*] Function "' + args.function + '" not support for ' + sst + ' :(')
    exit(0)

    
# comment
try:
    with open(args.input) as f:
        data = f.read().strip().split()
    if args.reverse:
        for ip in data:
            ipaddress.ip_address(ip)
    
    ipaddress.ip_address(args.server)
except Exception as e:
    print('[*]' + str(e))
    exit(0)


def DNSResolve(func, host, DNSServer):
    if func == 'nslookup':
        if sst == 'Windows':
            cmd = "nslookup " + host + " " + DNSServer
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
            out = result.stdout.split('s:')[-1].strip().split('\n')
            return [i.strip() for i in out]
        elif sst == 'Linux':
            cmd = 'nslookup '+host+' '+DNSServer+' 2>/dev/null | sed -n \'3,$ {/Address/p}\'|awk \'{print $2}\''
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
            out = result.stdout.strip().split('\n')
            return out
        
    elif func == 'dig':
        assert sst == 'Linux'
        cmd = 'dig +short '+host+' '+DNSServer+' 2>/dev/null'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
        out = result.stdout.strip().split('\n')
        return [i for i in out if 'error' not in i]
        
    elif func == 'host':
        assert sst == 'Linux'
        cmd = 'host '+host+' '+DNSServer+' 2>/dev/null | grep address | awk \'{print $NF}\''
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
        out = result.stdout.strip().split('\n')
        return out

    elif func == 'socket':
        return ['']
    
    else:
        # print('???')
        return ['']


def revDNSResolve(func, ip, DNSServer):
    if func == 'nslookup':
        if sst == 'Windows':
            cmd = 'nslookup '+ip+' '+DNSServer
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
            out = [i for i in result.stdout.strip().split('\n') if 'Name:' in i]
            return [i[5:].strip() for i in out]
        if sst == 'Linux':
            cmd = ' '.join(['nslookup',ip,DNSServer]) + '|grep name|awk \'{print $NF}\''
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
            out = result.stdout.strip().split('\n')
            return [i.strip('.') for i in out]
        
    elif func == 'dig':
        assert sst == 'Linux'
        cmd = 'dig +short -x '+ip+' '+DNSServer+' 2>/dev/null'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
        out = result.stdout.strip().split('\n')
        return [i.strip('.') for i in out if 'error' not in i]
    
    elif func == 'host':
        assert sst == 'Linux'
        cmd = 'host '+ip+' '+DNSServer+" 2>/dev/null | awk 'END{print $NF}'"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
        out = result.stdout.strip().split('\n')
        return [i.strip('.') for i in out if i != '3(NXDOMAIN)']
    
    elif func == 'socket':
        import socket
        host = [socket.gethostbyaddr(ip)[0]]
        return host
    
    else:
        # print('???')
        return ''


def output(res, ft, fn):
    if ft == '.json':
        import json
        with open(outputFile,'w') as f:
            json.dump(Result,f,indent=4)

    elif ft == '.xml':
        import xml.dom.minidom as mnd
        doc = mnd.Document()
        root = doc.createElement("data")
        doc.appendChild(root)
        for ip, hostnames in res.items():
            ip_element = doc.createElement("ip")
            ip_element.setAttribute("address", ip)
            for hostname in hostnames:
                hostname_element = doc.createElement("hostname")
                hostname_element.appendChild(doc.createTextNode(hostname))
                ip_element.appendChild(hostname_element)
            root.appendChild(ip_element)
        xml_str = doc.toprettyxml(indent="\t")
        with open(fn, "w", encoding="utf-8") as file:
            file.write(xml_str)

    elif ft == '.txt':
        with open(fn,'w') as f:
            for ip, hostnames in res.items():
                f.write(ip + ':' + ', '.join(hostnames) + '\n')

    elif ft == '.csv':
        import csv
        with open(fn, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["IP Address", "Hostnames"])
            for ip, hostnames in res.items():
                hostnames_str = ", ".join(hostnames)
                writer.writerow([ip, hostnames_str])
    else:
        # print('???')
        pass

if __name__ == '__main__':
    if args.reverse:
        func = revDNSResolve
    else:
        func = DNSResolve

    Result = {}
    for i,item in enumerate(data):
        try:
            print(str(i+1) + '/' + str(len(data)) + '\t' + item + '\r')
            Result[item] = func(args.function,item,args.server)
        except Exception as e:
            print('[*] '+ item + ': ' + str(e))
            Result[item] = []
            continue

    output(Result, outputFileType, outputFile)
    print('[*] Done, saved as ' + outputFile)
