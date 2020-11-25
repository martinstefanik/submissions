#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sends corrected submissions to the email address contained in the submission
file name.

See README.md for more details.
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

# Pattern for a corrected submission file name
PC = re.compile(r"(^(?!\.|.*\.\.).+[^.]\@.+\..+)_(\d+)_corrected\.pdf$")


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
    sheet_numbers = set([PC.match(f).group(2) for f in submission_files])
    if len(sheet_numbers) == 1:
        return False
    else:
        return True


def choose_by_email(submission_files):
    """
    Let the user choose which of the corrected submissions will be returned by
    the email address in the submission file names.

    Args:
        submission_files (list of str): List of submission files to start from.

    Returns:
        list of str: List of email addresses to which the corresponding
            corrected submissions are to be sent.
    """
    addresses = [PC.match(f).group(1) for f in submission_files]

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
            return submission_files
        else:
            try:
                selected = [int(n) for n in selected.split()]
            except ValueError:
                print('\nInvalid input. Try again.\n')
                continue
            if min(selected) < 1 or max(selected) > len(addresses):
                print('\nInvalid input. Try again.\n')
                continue
            else:
                selected = [submission_files[i - 1] for i in selected]
                return selected


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


def send_solutions(con, selected, name=None, email=None):
    """
    Send out the selected corrected submissions.

    Args:
        selected (list of str): List of corrected submission file to be sent
            out.
        con (smtplib.SMTP): Active SMTP connection to the ETH mail server.
        name (str): Space-separate name and surname of the sender. This will be
            used in the email header as well as in the signature in the body of
            the email. Defaults to `None`, in which case the user is prompted
            for these.
        email (str): Sender's email address. Defaults to `None` in which case
            the user is prompted for it.
    """
    pairs = [PC.match(f).group(1, 0) for f in selected]
    addresses = [p[0] for p in pairs]
    sheet_number = PC.match(selected[0]).group(2)

    # Ask for confirmation of the submissions to be sent
    _show_confirmation_prompt(con, addresses)

    # Ask for the name to be included in the email signature
    if name is None:
        name = ''
        while name == '':
            name = input('Your first name: ')
        surname = ''
        while surname == '':
            surname = input('Your surname: ')
        name = f'{name} {surname}'

    # Send out the corrected submissions
    checked = False  # indicates whether the sender's email address was checked
    unsuccessful = addresses.copy()
    for address, sf in pairs:

        # Construct the base of the message
        msg = MIMEMultipart()
        msg['To'] = address
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = f'Corrected submission {sheet_number}'

        # Attach the submission file
        with open(sf, 'rb') as f:
            attachment = MIMEApplication(f.read(), Name=sf)
        attachment['Content-Disposition'] = f'attachment, {sf}'
        msg.attach(attachment)

        # Attach the text
        msg.attach(MIMEText(
            'Hi,\n\nThe correction of your submission for exercise sheet '
            f'{sheet_number} is attached.\n\nBest '
            f"regards,\n{name}"
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
        print('\nAll correction submissions were sent out successfully!')
    else:
        print('\nFailed to send out corrected submissions to:\n')
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
    submissions = [f for f in os.listdir() if PC.fullmatch(f)]

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
    selected = choose_by_email(submissions)
    con = connect()
    send_solutions(con, selected, name, email)
    con.quit()


if __name__ == '__main__':
    main()
