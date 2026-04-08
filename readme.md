# annaScript Studio

![Python](https://img.shields.io/badge/Python-3.13.2-blue)
![Version](https://img.shields.io/badge/Version-1.1.3-brightgreen)
![Platform](https://img.shields.io/badge/Platforms-Windows-blue)
![Platform](https://img.shields.io/badge/Platforms-Linux-blue)

![Dependencies](https://img.shields.io/badge/Dependencies-PySide6-lightgrey)
![Dependencies](https://img.shields.io/badge/Dependencies-PySide6_Addons-lightgrey)
![Dependencies](https://img.shields.io/badge/Dependencies-PySide6_Essentials-lightgrey)

## Introduction

*annaScript* is a simple, easy-to-use markup language that compiles to HTML. It features a rich, simple syntax and an easily extendible macro system. Because *annaScript* uses a minimalistic approach to parse data, realtime compilation is possible without any noticable lag (Average Compile Time: < 30ms).

*annaScript Studio* is a sophisticated editor for *annaScript* with realtime preview.
With it, the language becomes the perfect solution for note taking, especially if you like *markdown* syntax but miss CSS features.

Like mentioned above, extending or adjusting the language is easy due to the macro and theme system. All themes are defined through CSS files. In this repository, you'll find three base themes you can use out of the box, modify or use as template to create new ones.

## Get Started

### Download and Usage

#### Compiled Version (Recommended for Windows)

If you are on Windows, the ```.exe``` version is the easiest way to get started.
Simply download the installer from the latest release and run it. It will not only
install *annaScript* and *annaScript Studio* together but will also register the filetype
```.ascr``` which makes using the editor a lot easier.

#### Python Version (Any other OS)

If you want to use the Python version, simply follow these instructions:

1. Download the source code from the latest release
2. Install all dependencies with ```pip install -r "requirements.txt```
3. Run main.py

You can also build *annaScript Studio* for any other OS using PyInstaller. Make sure to enable dynamic linking in order to comply with the *PySide6* license.

### Syntax and Macros

Most of the syntax is similar to *markdown*, with some features extending its functionality. Below you'll find all current elements of *annaScript*'s syntax.

#### Meta tags

These tags that have to be placed at the beginning at the document (but aren't necessary) define meta elements of the document, such as author, title and style. The style tag defines the CSS theme that is linked in the HTML.
Below are all current meta tags available:

```annascript
@title: My Document
@author: Annabeth Kisling
@style: default
@darkmode: true
```

#### Headings

Headings use the same syntax as *markdown*. They are directly equivalent to ```<h1>```-```<h6>``` tags in HTML.

```annascript
# H1 heading
## H2 heading
### H3 heading
#### H4 heading
```

#### Paragraphs

Paragraphs are separated by at least one blank line.

```annascript
This is paragraph one.
It continues here.

This is paragraph two.
```

#### Formatting

Text formatting works by wrapping text in certain characters. Currently, *annaScript* supports **bold**, *italic*, underline and highlighted texts, `code blocks` and sub/superscript.

```annascript
*italic*

**bold**

***both***

==highlight==

`code block`

^^super^^

,,sub,,

_underline_
```

#### Links

Links follow the same syntax as in *markdown* as well.

```annascript
[Visit My Website](http://tk-dev-software.com)
```

#### Lists

There is support for ordered and unordered lists, as well as for sub items.

Unordered:

```annascript
- Item A
- Item B
    - Subitem
    - Subitem
```

Ordered:

```annascript
1. First
2. Second
```

#### Macros

Macros are the highlight of *annaScript* and are the easiest to add your own elements to your document. All macros follow the same syntax rules:

```annascript
::type optional-attributes
content inside macro...
::
```

There are a few built-in macros:

```annascript
::box type=danger title="Attention!"
Danger awaits...
::

::box type=warning title="Warning!"
Be warned!
::

::box type=info title="Information"
Be informed!
::

::def
(a+b)^^2^^ = a^^2^^ + 2ab + b^^2^^
::

::note
Remember this!
::

::box
Hello, I'm just a box!
::

::center
Centered text
::
```

These macros are equivalent to CSS classes, which makes it easy to add your own. Simply add a new class to your theme CSS file and use its name inside the macro definition.

#### Charts

Charts in *annaScript* are also macros declared like mentioned above. Currently, there are two types of charts supported:

- **Pie Charts**: are rendered using CSS gradients and include a legend.
- **Bar Charts**: are also rendered using CSS and currently do not include a legend.

To use charts, first declare a macro using the syntax like above. You'll need to define the type of the macro (pie/bar). You can also set a title shown above the chart.

Then, inside the macro, create a table with two columns (see next chapter for reference). In the first column, define the data label and, in the second column, define the data itself. The data entry must either be a full integer or a float, separated by a dot (".").

**All data entries inside of one pie chart must equal 100, or else the chart will not reflect accurate data.**

```annascript
::chart type=pie title="My awesome pie chart"
|Label 1|20.5|
|Label 2|19.5|
|Label 3|60.0|
::
```

```annascript
::chart type=bar title="My awesome bar chart"
|2023|20000|
|2024|25000|
|2025|27000|
::
```

The compiler will now try and create the selected chart type using the provided data.

If the provided data is faulty, the chart won't be shown and an error message like this will appear instead:

```Error creating chart, check table data!```

If the declared chart type isn't recognized (or if it isn't specified), this error message will be shown:

```Unsupported chart type```

If there is no recognisable data inside the chart macro, this error message will be shown:

```No data provided.```

#### Tables

Tables are written using the separator ("|"). If there are dashes below the first row, the row becomes a table header.

```annascript
| Name  | Age | Grade |
|-------|-----|-------|
| Alice | 17  | A     |
| Bob   | 16  | B     |
```

## Modifying and Developing with annaScript

**Note: This version of annaScript is mainly meant for casual usage. If you want to modify annaScript, I'd recommend using the barebone version [in this repository](https://github.com/hasderhi/annascript)**

### Overview

When I started creating *annaScript*, it was because I was fed up with taking notes at school in Word and struggling with its formatting system. I tried using *markdown* but quickly realised that it was missing some features like sub/superscript or macros. Also, it was a problem that different *markdown* engines used different syntax versions.

Because of this, I decided to build my own markup language - *annaScript* was born. The engine itself is really basic and features the typical "interpreted language" features like a simple parser, tokenizer, AST nodes and a HTML renderer. However, because this language is very much tailored to my own specific needs, I decided to keep it easily customiziable so anyone can adjust the syntax to their likings.

### Macros and Themes

If you simply want to create your own elements, you don't need to modify the engine itself. You can simply create your theme (or modify an existing one) and add your macro's CSS definitions inside a CSS class.

Creating and using your own themes is really simple: Navigate to the ```/themes``` folder and create a new folder with your desired theme name (e.g. "myTheme"). Inside that folder, create two CSS files: ```light.css``` and ```dark.css```. Now, you can write your own style definitions for your documents. My recommendation is to start of by modifying one of the built-in themes to understand what elements need to have style attributes.

With the new theme created, import and use it in your document by placing this meta tag at the top:

```@style: myTheme```

Optionally, you can also use dark mode (default is light):

```@darkmode: true```

## Information

This project is the counter part to *annaScript*, the barebones version of annaScript without the editor. Check it out [on its GitHub repository](https://github.com/hasderhi/annascript)!

Whilst *annaScript* itself isn't using any external dependencies, *annaScript Studio* uses *PySide6* for its GUI. All Qt libraries are used with dynamic linking, which complies to the license.

All *annaScript* compiler source code and the built-in themes are made by the author and subject to her copyright. All code is released under the MIT-License (see ```license.md```) and therefore allows anyone to modify, copy, use or release it under the condition the author's work is credited and the license is included.

If you created a theme and think it could be useful for others, feel free to make a pull request to the repo!

## Author

Annabeth Kisling

[annabeth@tk-dev-software.com](mailto:annabeth@tk-dev-software.com)

[tk-dev-software.com](https://tk-dev-software.com)
