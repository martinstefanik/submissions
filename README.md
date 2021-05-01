# Submissions

This repository contains a script for returning _corrected_ solutions to exercise sheets submitted by students at ETH Zurich to their email addresses. The script is a simple solution to having students that are not formally registered to a particular course attend the exercise class and submit their solutions to the posted exercise sheets. It complements well the approach of having a directory with 'upload only' permission to which the students simply upload their solutions.

## Requirements

The script should run on any Unix-like operating system such as Linux or macOS with a Python interpreter version 3.6 or higher. It does not have any dependencies outside of the Python standard library, so it does not require
installation of any external packages.

## How to Use

In order for the script to be usable, the following must be ascertained:

* Each corrected submission file _must_ be a single PDF file.
* Each corrected submission file _must_ be named as `{email address}_{exercise sheet number}_corrected.pdf`. The parts surrounded by brackets are placeholders that should be replaced by the email address at which the student wants to receive the corrected solution and the number of the exercise sheet to which the solution pertains, respectively. A correctly named solution file for exercise sheet 1 is for instance given by `john.doe@institution.com_1_corrected.pdf`. The easiest way to go about this is to have students submit their solutions as a single PDF file that is named in the same way but with '_corrected' removed.
* The directory in which the script is executed _cannot_ contain corrected submission files for multiple exercise sheets.

The script can be executed using one of the following options:

* You _copy_ the script into the directory where you want to run it (that is the directory containing the corrected submission files), you open a terminal in that location and run `python3 submissions.py`.
* You open up a terminal and change your directory to the one with the corrected submissions that you want to send back and run the same command as above but with the script name replaced by full path to the script. For instance `python3 ~/course_name/exercise-1/submissions.py`.
* You copy the script to a location included in the `PATH` environment variable. This will allow you to simply run `submissions.py` as a command from anywhere. 

Upon execution, the script will prompt you for authentication to the mail server of ETH Zurich and for some other data. The code can be easily modified for other institutions.

You will also be prompted to choose which of the corrected submission files found in the directory should be sent out. In case the email address contained in the submission file name is not correct, you will receive a delivery error email at your email address directly.

## Configuration file

In order not to be prompted for you name and email address every time you run the script, you can include your name and **ETH email address** in the configuration file `~/.config/submissions`. The configuration file should be formatted as a JSON file and your name and email stored with the keys _name_ and _email_, respectively.

An example file looks like:

```console
{
    "name": "John Assistant",
    "email": "john.assistant@math.ethz.ch"
}
```
