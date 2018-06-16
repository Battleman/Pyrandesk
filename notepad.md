dconf write a new key : `dconf  write KEY VALUE`

to write string value `foo`, key must be `"'foo'"`

set wallpaper : 
```
    dconf write /org/gnome/desktop/background/picture-uri "'file:///home/user/path/to/image.jpg'"
```
read current:
    `dconf read /org/gnome/desktop/background/picture-uri`

result is
    `'file:///home/user/path/to/image.jpg'`
need to parse !




