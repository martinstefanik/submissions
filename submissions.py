#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sends corrected submissions to the email address contained in the submission
file name.

The script will only work if there are corrected submissions for only one
exercise sheet in the directory that in which the script is ran. See
README.md for more details.
"""

import os
import sys
import re
import json
import smtplib
import getpass
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.utils import formatdate, formataddr


def connect():
    """
    Prompt for credentials and establish a connection the ETH mail server.

    Returns:
        smtplib.SMTP: Active SMTP connection.
    """
    con = smtplib.SMTP(host='mail.ethz.ch', port=587)
    con.starttls()
    while True:
        user_name = input('\nNETZ user name: ')
        pwd = getpass.getpass('Password: ')
        try:
            con.login(user_name, pwd)
        except smtplib.SMTPAuthenticationError:
            print('\nWrong user name or password. Try again.')
        except smtplib.SMTPException:
            print('\nCould not connect to the server. Try again.')
            sys.exit()
        else:
            print('\nConnection established!')
            break

    return con


def has_multiple_sheets(submission_files):
    """
    Check whether there are corrected submissions for multiple exercise sheets
    among the given submission files.

    Args:
        submission_files (list of str): List of submission files to be checked.

    Returns:
        bool: Indicates the multiplicity.
    """
    pattern = re.compile(r'\d+_corrected\.pdf$')
    endings = [re.findall(pattern, f)[0] for f in submission_files]
    if len(set(endings)) == 1:
        return False
    else:
        return True


def get_email_addresses(submission_files):
    """
    Generate the list of email addresses to which the corresponding corrected 
    submissions are to be returned based on user's input.

    Args:
        submission_files (list of str): List of submission files to start from.

    Returns:
        list of str: List of email addresses to which the corresponding
            corrected submissions are to be sent.
    """
    addresses = _extract_email_addresses(submission_files)

    # Print a numbered list of email addresses to select from
    numbered = []
    for num, address in zip(range(1, len(addresses) + 1), addresses):
        numbered.append(f'[{num}] {address}')
    print('\nThis directory contains submissions from: \n')
    print('\n'.join(numbered), '\n')

    # Selection prompt
    while True:
        selected = input(
            "Which submissions to send out? Give a space-separated list of\n"
            "numbers from the list above or type 'all' (unquoted) if you\n"
            "want to send out all submissions:\n\n"
        )
        if not selected:
            print('Invalid input. Try again.\n')
            continue
        if selected == 'all':
            return addresses
        else:
            try:
                selected = [int(a) for a in selected.split()]
            except ValueError:
                print('\nInvalid input. Try again.\n')
                continue
            if min(selected) < 1 or max(selected) > len(addresses):
                print('\nInvalid input. Try again.\n')
                continue
            else:
                addresses = [addresses[i - 1] for i in selected]
                return addresses


def _extract_email_addresses(submission_files):
    """
    Extract email addresses from the given corrected submission files.

    Args:
        submission_files (list of str): List of corrected submission files
            from which email addresses are to be extracted.

    Returns:
        list of str: List of extracted email addresses.
    """
    addresses = []
    for sub in submission_files:
        address = '_'.join(sub.split('_')[:-2])
        addresses.append(address)

    return addresses


def read_config_file():
    """
    Read the config file for the script.

    Returns:
        tuple (str, str): Name and email address of the sender. Returns `None`
            for both if the config file does not exist or if its contents are
            not correct.
    """
    config_file = os.path.join(
        os.path.expanduser('~'), '.config', 'submissions'
    )
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
            name = data.pop('name', None)
            email = data.pop('email', None)
    except (json.JSONDecodeError, FileNotFoundError):
        return None, None
    else:
        return name, email


def send_solutions(con, addresses, name=None, email=None):
    """
    Send corrected submission files to the corresponding email addresses.

    Args:
        addresses (list of str): List of email addresses to which
            the corresponding corrected submission files should be sent.
        con (smtplib.SMTP): Active SMTP connection to the ETH mail server.
        name (str): Space-separate name and surname of the sender. This will be
            used in the email header as well as in the signature in the body of
            the email. Defaults to `None`, in which case the user is prompted
            for these.
        email (str): Sender's email address. Defaults to `None` in which case
            the user is prompted for it.
    """
    # Ask for confirmation of the submissions to be sent
    _show_confirmation_prompt(con, addresses)

    # Ask for the name to be included in the signature
    if name is None:
        name = ''
        while name == '':
            name = input('Your name and surname: ')

    # Send the submissions
    checked = False  # indicates whether the sender's email address was checked
    unsuccessful = addresses.copy()
    for address in addresses:

        # Construct the base of the message
        msg = MIMEMultipart()
        msg['To'] = address
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = 'Corrected submission'

        # Get the corrected submission PDF corresponding to `address`
        pattern = re.compile(address + r'_\d+_corrected\.pdf')
        submission = [f for f in os.listdir() if pattern.fullmatch(f)][0]

        # Attach the submission file
        with open(submission, 'rb') as f:
            attachment = MIMEApplication(f.read(), Name=submission)
        attachment['Content-Disposition'] = f'attachment, {submission}'
        msg.attach(attachment)

        # Attach the text
        msg.attach(MIMEText(
            'Hi,\n\nThe corrected submission of yours is attached.\n\nBest '
            f'regards,\n{name}'
        ))

        # Fill out the sender's email address and send the message
        if not checked:
            while not checked:  # check sender's address with the first email
                if email is None:
                    source_address = input('Your ETH email address: ')
                else:
                    source_address = email
                addr = formataddr((str(Header(name)), source_address))
                if 'From' in msg:
                    msg.replace_header('From', addr)
                else:
                    msg['From'] = addr

                try:
                    con.send_message(msg)
                    checked = True  # mark sender's address as checked
                    unsuccessful.remove(address)
                except (smtplib.SMTPSenderRefused, smtplib.SMTPDataError):
                    if email is None:
                        print('\nInvalid. Try again.')
                    else:
                        print("Invalid email in 'submissions' config file.")
                        con.quit()
                        sys.exit()
                except smtplib.SMTPServerDisconnected:
                    print('\nFailed. Try re-running the script.')
                    sys.exit()
                except smtplib.SMTPException:
                    unsuccessful.remove(address)
                    break

        else:
            msg['From'] = addr
            try:
                con.send_message(msg)
                unsuccessful.remove(address)
            except smtplib.SMTPException:
                unsuccessful.remove(address)
                break

    if not unsuccessful:
        print('\nAll submissions were sent successfully!')
    else:
        print('\nFailed to send corrected submissions to:\n')
        print('\n'.join(unsuccessful))


def _show_confirmation_prompt(con, email_addresses):
    """
    Show a list of email addresses to which corrected submissions are to be
    returned and ask for a confirmation.

    Args:
        con (smtplib.SMTP): Active SMTP connection to the ETH mail server.
        email_addresses (list of str): List of email addresses.
    """
    print('\nCorrected submissions will be sent to:\n')
    print('\n'.join(email_addresses), '\n')
    proceed = ''
    while proceed != 'y' and proceed != 'n':
        proceed = input('Do you want to proceed? [y/n]: ')
        if proceed == 'y':
            pass
        elif proceed == 'n':
            print('\nAborting.')
            con.quit()
            sys.exit()
        else:
            print("One of 'y' or 'n' required")


def main():
    # Get the list of corrected submission files in the directory
    pattern = re.compile(r'.*@.*\..*_\d+_corrected\.pdf')
    submissions = [f for f in os.listdir() if pattern.fullmatch(f)]

    # Sanity checks
    cwd = os.getcwd()
    if not submissions:
        print(f'No submissions in {cwd}.')
        sys.exit()
    elif has_multiple_sheets(submissions):
        print(f'Corrected submissions for multiple sheets in {cwd}.')
        sys.exit()

    # Read the config file
    name, email = read_config_file()

    # Send out the corrected submissions
    addresses = get_email_addresses(submissions)
    con = connect()
    send_solutions(con, addresses, name, email)
    con.quit()


if __name__ == '__main__':
    main()
