![Logo](/Utilities/Screenshots/Logo_new.png)

A fully custom Fire Emblem fangame created entirely in Python.

Fire Emblem: The Lion Throne is a custom Fire Emblem fangame. Much of my inspiration for the game was drawn from the GBA and Tellius games. 

Because this was coded entirely from scratch, I am not bound by the limitations of the GBA. 

The Lion Throne has innovative objectives, powerful new items, custom classes, a fully functioning skill system with activated skills, a Tellius-style base menu, and much more!

![TitleScreen](/Utilities/Screenshots/TitleScreen3.png) 
![Range](/Utilities/Screenshots/Range1.png)
![Skill](/Utilities/Screenshots/Skill1.png)
![Prep](/Utilities/Screenshots/Prep1.png)
![Conversation](/Utilities/Screenshots/Conversation1.png) 
![Convoy](/Utilities/Screenshots/Convoy1.png)
![Item](/Utilities/Screenshots/Item1.png) 
![Aura](/Utilities/Screenshots/Aura1.png)
![Base](/Utilities/Screenshots/Base2.png)

# Lex Talionis

Lex Talionis is the custom Fire Emblem engine that runs The Lion Throne. If you've wanted to make your own Fire Emblem fangame but were fed up with the hackery thats required to master ROM-hacking, or you just want to work with total control over the code itself, Lex Talionis is for you. 

Not interested in coding? That's fine -- one can create a whole new game with touching any code. Just modify the "Data" folder, which only contains sprites, text files, and xml files! But if you have Python experience or want to do something I did not expect, the code is entirely open-source and can be changed to meet your needs.

I am planning to create a tutorial on how to use the Lex Talionis engine.

Both the engine and the fangame are still in Alpha, so there may (and probably are) bugs in the code. Tread carefully.

### More Screenshots (v0.1):
![Screenshot 1](/Utilities/Screenshots/Attack.png) ![Screenshot 2](/Utilities/Screenshots/Chapter10.png)
![Screenshot 3](/Utilities/Screenshots/InfoMenu.png) ![Screenshot 4](/Utilities/Screenshots/Chapter30.png)
![Screenshot 5](/Utilities/Screenshots/Chapter20.png) ![Screenshot 6](/Utilities/Screenshots/Narration0.png)

### More Screenshots (v0.2)
![Screenshot 7](/Utilities/Screenshots/Combat.png) ![Screenshot 8](/Utilities/Screenshots/TitleScreen.png)
![Screenshot 9](/Utilities/Screenshots/HealShow.png) ![Screenshot 10](/Utilities/Screenshots/TransitionScreen.png)
![Screenshot 11](/Utilities/Screenshots/FreeScreen.png) ![Screenshot 12](/Utilities/Screenshots/Narration1.png)

## Default Controls:

 - Arrow keys move the cursor.

 - {X} is the 'A' button. Go forward.

 - {Z} is the 'B' button. Go backward.

 - {C} is the 'R' button. It gives the player additional info.

 - {S} is the 'Start' button. 

 - {A} is the 'L' button.

These defaults can be changed within the game or in the Data/config.txt file

## Getting Started

If you don't want to go through the hassle of running this with Python + Pygame, you can download this executable instead (Windows only, unfortunately).

**DOWNLOAD HERE (old)**: http://www.mediafire.com/download/rgwn1xo9oepqpb2/lex-talionis-exe.zip (release v0.01).

However, if you are familiar with Python, Pygame, and Git, read on to find out how to get a fully customizable version of this on your machine.

### Prerequisites

To run The Lion Throne, you will need to download and install the following:

* [Python 2.7.x+](https://www.python.org/downloads/release/python-2712/) - Python 3.x will not work
* [Pygame 1.9.1+](http://www.pygame.org/download.shtml) - The framework used to handle rendering and sound

### Installing

This section requires git.
If you don't have git, install it from here: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git.

To get the Lex Talionis engine code on your machine, create a new folder.
Then, type:

```
git clone https://github.com/rainlash/lex-talionis
```

You will also need to download the audio files, which are not stored on Git because of their size. 

On Dropbox here: https://www.dropbox.com/sh/slbz2t7v1fc6uao/AACiznGLm442qcdOAGbQtnmwa?dl=0. 

On the top right of the page, click "Download", then click "Direct Download".

Once the audio files are downloaded, extract the zip file and move or copy the Audio folder to the lex-talionis directory (the directory that contains Main.py).

Once Lex Talionis has been cloned to your machine, from that same directory, you can run The Lion Throne by typing:

```
python Main.py
```

A small screen should pop up on your computer, displaying the logo. Don't worry if it takes a minute or two the first time it is run. It is just taking the time to parse the code into compiled binary files.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details