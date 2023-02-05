# Novel downloader

Python utility to download novels from `novelabook.link` as a single HTML file
that can be read on Kindle devices.

## Motivation

A very special person I know is reading a novel from `novelabook.link`.
Initially, she was reading it on her phone, but we know backlit screens strain
our eyes and reduce the quality of our sleep.
I suggested her to grab my old Kindle instead as it has an experimental web
browser and I haven't used it in a while.

This setup has served her for a while; but because she only has time to read
at night and this old 2014 Kindle doesn't have a front light, she was
still straining her eyes by reading in the dark (she doesn't always have a
nightstand lamp at hand).

So I bought the newest basic Kindle. It has 300 ppi, a web browser and a front
light! And since it's the newest Kindle available, it should be faster, right?
W-R-O-N-G.
The web browser is not experimental anymore, but for some reason it's still
sluggish and what's worst: it doesn't allow zooming on any page! So the text
looks really tiny.

I was planning on giving this new Kindle to her as a present, but the above
really undiscouraged me to do so. Then I remembered I used to send html/epub
files to my Kindle via email.

So I thought, why not create a Python script to open the home page of the novel,
go through each page of the chapter listing, extract the URLs of all chapters,
download the chapter contents, and then put the contents back into a single and
minimal HTML page? 

And I started this project in the middle of a cold night.

Now this very special person I know is reading the novel on her new Kindle <3

## Next steps

- Add table of contents: To make it easier to navigate through pages/chapters.
- Refactoring: I really want to refactor this project, I made it in one night
while sleepy, so it might have some weird implementations/patterns.