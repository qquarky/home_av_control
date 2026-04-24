# Purpose
I needed a simple way to interact with my Extron/Anthem devices
over the network so I developed these files as a way to do that.

The main motivation was for creating a custom home entertainment
control system that my family could use to easily set up the 
TV and receiver to the correct inputs and outputs.

For example, my son uses a StreamDeck to choose what device
he wants to display on the TV while my wife uses a website.

Both of these methods will use the same libraries to control
the Extron/Anthem devices to:
  1. Turn on the TV
  2. Turn on the AV Receiver
  3. Change the TV input to the correct source
  4. Change the Extron input to the selected device

# Installation
Install the requirements.txt file

##### Python 3.13
telnetlib has been removed from python 3.13, you can use
standard-telnetlib as a drop in replacement, if needed.
