import os
import sys
# Paramiko is used for SSH
from paramiko import SSHClient, AutoAddPolicy
# Import smtplib for the actual sending function
import smtplib
from email.message import EmailMessage
# Using dotenv so you dont have to hardcode the passwords/servers. So that they can easily be modified later
from dotenv import load_dotenv

load_dotenv()

#Environment variables
EMAIL_ADDRESS = os.environ.get('EMAIL_USER')
EMAIL_PASSWORDS = os.environ.get('EMAIL_PASS')

# host = "192.168.1.178"
# port = 22
# username = "bobby"
# password = "test"

file_name, distro, host, port, username, password = sys.argv

print(f"Running {sys.argv[0]}...")

def commands_per_distro(distro): # disk_space, check_for_updates, services_list
    if distro == 'ubuntu':
        return ["df | awk '{print $1,$5}'",'apt list --upgradable','service --status-all']
    if distro == "fedora":
        return ["df | awk '{print $1,$5}'",'sudo dnf check-update',' systemctl list-units --type=service']


#Send email part
server_maintainers = ['your@emailaddress.com'] # Could also be read from a file

def send_mail(warning, problem):
    msg = EmailMessage()
    msg.set_content(f"Please check, {problem} \n {warning} ")
    msg["Subject"] = "Errors that require your attention" #Could be more specific
    msg["From"] = 'Bobby'
    msg["To"] = server_maintainers


    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORDS)
        smtp.send_message(msg)



##SSH Part
def remoteCMD(command, filename): #Username, Host 
    host_keys= 'C:/Users/Bobby/.ssh/known_hosts'
    ssh = SSHClient()
    # ssh.set_missing_host_key_policy(AutoAddPolicy()) Used if the SSH-key can always be trusted
    ssh.load_host_keys(host_keys) #TODO iterate over multiple if needed
    ssh.load_system_host_keys() #TODO Check if RSA key has changed (Man-in-the-middle attack)
    try:
        ssh.connect(host, port, username, password)
        stdin, stdout, stderr = ssh.exec_command(command)
    except:
        send_mail('Please check', f"Could not connect to {host}")
        sys.exit()
    lines = stdout.readlines()
    #Also possible to write lines into logs/files
    # for line in lines: 
    #     f = open(f"{filename}.txt", "a")
    #     f.write(line)
    #     f.close()
    return lines


disk_space, check_for_updates, services_list = commands_per_distro(distro)


available_disk_space = remoteCMD(disk_space, 'DiskSpace')
update_list = remoteCMD(check_for_updates, 'UpdateList')
running_services = remoteCMD(services_list, 'CriticalServices')


# Get list of all critical services that are not running

def service_not_running(services_list):
    critical_services_list = ['ssh', 'irqbalance', 'uuidd', 'apache', 'lvm2'] #TODO Should proably be read from a file
    service_errors = []
    for service in services_list:
        services = str(service).strip()
        if services[0:5] == "[ - ]":
            if services[7:] in critical_services_list:
                service_errors.append(services[5:].strip())
    return service_errors

# Calculate if disk space is over the threshold
def calculate_space(available_disk_space):
    disk_space_critical_amount = 85
    converted_list = []
    _header, *line = available_disk_space
    for disk in line:
        disk_name, disk_space = disk.strip().split()
        
        if disk_space_critical_amount < int(disk_space[:-1]):
            converted_list.append(f"{disk_name}\t{disk_space} - Over acceptable limit")
        else:
            converted_list.append(f"{disk_name}\t{disk_space}")
        
    return converted_list


if service_not_running(running_services):
    send_mail(service_not_running(running_services), 'current services are not online')
if update_list:
    send_mail('\n'.join(update_list),'there are new updates')
if available_disk_space:
    send_mail('\n'.join(calculate_space(available_disk_space)), 'Your disk space is low on some disks')
    
print("Done")
