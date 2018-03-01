#! /usr/bin/env python

import io
import re
import tkinter as tk
import requests
import time
from tkinter import *
from tkinter import ttk
from bs4 import BeautifulSoup
from enum import Enum
from PIL import Image, ImageTk
from urllib.request import urlopen

BACKGROUND_COLOUR 		= "black"
FOREGROUND_COLOUR 		= "white"
ICON_BITMAP_LOCATION 	= "something.ico"
APP_TITLE 				= "R€ddit"
SCREEN_WIDTH 			= 1920
SCREEN_HEIGHT 			= 1080
SIZE_BORDER_RATIO		= 0.9
TRUE_SCREEN_HEIGHT		= SCREEN_HEIGHT * SIZE_BORDER_RATIO
TRUE_SCREEN_WIDTH		= SCREEN_WIDTH * SIZE_BORDER_RATIO
POST_Y_PADDING 			= 8
DEFAULT_SUBREDDIT 		= ""
DOMAIN 					= "https://www.reddit.com"
HEADERS 				= {'User-agent': 'redditClone1.0'}
COMMENT_FONT 			= ("Helvetica", 10)
SELF_POST_FONT 			= ("Helvetica", 13)
TITLE_FONT 				= ("Helvetica", 16)

class ToolKit:
	_nonbmp = re.compile(r'[\U00010000-\U0010FFFF]')

	def surrogatePair(self, match):
		char = match.group()
		assert ord(char) > 0xffff
		encoded = char.encode('utf-16-le')
		return (
			chr(int.from_bytes(encoded[:2], 'little')) + 
			chr(int.from_bytes(encoded[2:], 'little')))

	def withSurrogates(self, text):
		return self._nonbmp.sub(self.surrogatePair, text)
		
	def validateChars(self, string):
		for char in string:
			if ord(char) > 0xffff:
				string = string.replace(char, self.withSurrogates(char))
		return string
		
	def removePrefix(self, text, prefix):
		if text.startswith(prefix):
			return text[len(prefix):]
		return text 

TOOLKIT = ToolKit()

class MediaType(Enum):
	TEXT 	= 1
	IMAGE 	= 2
	GIF 	= 3
	VIDEO 	= 4

class Roddit(tk.Tk):
	def __init__(self, *args, **kwargs):
		tk.Tk.__init__(self, *args, **kwargs)
		#tk.Tk.iconbitmap(self, default=ICON_BITMAP_LOCATION)
		tk.Tk.wm_title(self, APP_TITLE)
		tk.Tk.geometry(self, '{}x{}'.format(SCREEN_WIDTH, SCREEN_HEIGHT))
		
		container = tk.Frame(self)
		container.pack(side="top", fill="both", expand = True)
		container.grid_rowconfigure(0, weight=1)
		container.grid_columnconfigure(0, weight=1)
		self.container = container
		
		s = ttk.Style()
		s.configure("GENERIC.TButton", background=BACKGROUND_COLOUR)
		
		self.frames = {}
		
		for F in (MainPage, CommentsPage, ContentPage):
			frame = F(container, self)
			self.frames[F] = frame
			frame.grid(row=0, column=0, sticky="nsew")
		
		self.showFrame(MainPage)
		
	def showFrame(self, controller):
		frame = self.frames[controller]
		frame.tkraise()
		
class MainPage(tk.Frame):
	list_of_posts = []
	
	def __init__(self, parent, controller):
		tk.Frame.__init__(self, parent, bg=BACKGROUND_COLOUR)
		subreddit_box 	= Entry(self, width=30)
		#test = Text(self, width=20, state=DISABLED, bg=BACKGROUND_COLOUR, relief=FLAT)
		go_button 		= ttk.Button(self, text="Go", 
							command=lambda: self.refreshPage("/r/" + subreddit_box.get().strip("\n")), style="GENERIC.TButton")
		clear_button 	= ttk.Button(self, text="Clear",
							command=lambda: subreddit_box.delete(0, END), style="GENERIC.TButton")
		subreddit_box.pack()
		go_button.pack()
		clear_button.pack()
		#test.tag_bind("Enter>", show_hand_cursor)
		#test.pack()
		subreddit_box.bind("<Return>", lambda x: self.refreshPage("/r/" + subreddit_box.get().strip("\n")))
		self.controller = controller
		self.refreshPage(DEFAULT_SUBREDDIT)

	def refreshPage(self, subreddit):
		url = DOMAIN + subreddit
		
		print("\nUrl is", url)
		
		request = requests.get(url, headers = HEADERS)
		html = request.text
		soup = BeautifulSoup(html, 'html.parser')
		title = soup.find('title').string

		print("status code is", request.status_code)
		
		self.clearPage()
		self.displayContent(request, soup, title, subreddit)
			
	def displayContent(self, request, soup, title, subreddit):
		if request.status_code == 200:
			if title != "search results":
				thread_titles 	= soup.select("a.title.may-blank")
				thread_links 	= soup.select("a.bylink.comments.may-blank")
				content_domains = soup.select("span.domain a")
				if thread_titles:
					for thread_title, thread_link, content_domain in zip(thread_titles, thread_links, content_domains):
						self.addLabel(thread_title.string, thread_title['href'], thread_link['href'], content_domain.string, subreddit)
				else:
					self.addLabel("This subreddit appears to be empty", None, None, None, None)
			else:
				self.addLabel("/r/" + subreddit + " could not be found", None, None, None, None)
		else:
			self.addLabel("Error: Received status code " + str(request.status_code), None, None, None, None)		
			
	def clearPage(self):
		for post in self.list_of_posts:
			post.thread_title_label.destroy()
		self.list_of_posts.clear()
			
	def addLabel(self, message, content_link, thread_link, content_domain, subreddit):
		message = TOOLKIT.validateChars(message)
		label = tk.Label(self, text=message, font=COMMENT_FONT, anchor='w', bg=BACKGROUND_COLOUR, fg=FOREGROUND_COLOUR)
		label.bind("<Enter>", lambda x: self.config(cursor="hand2"))
		label.bind("<Leave>", lambda x: self.config(cursor="arrow"))
		post = Post(label, content_link, thread_link, content_domain, subreddit)
		label.bind("<Button-1>", lambda x: self.controller.frames[CommentsPage].loadComments(post))
		self.list_of_posts.append(post)
		label.pack(fill='both', pady=POST_Y_PADDING)
		
class CommentsPage(tk.Frame):
	list_of_elements = []
	
	def __init__(self, parent, controller):
		tk.Frame.__init__(self, parent, bg=BACKGROUND_COLOUR)
		back_button = ttk.Button(self, text="Go back", command=lambda: controller.showFrame(MainPage), style="GENERIC.TButton")
		back_button.pack()
		self.controller = controller
		
	def loadComments(self, Post):
		url 				= Post.thread_link
		print("\nThread URL is", url)
		request 			= requests.get(url, headers=HEADERS)
		html 				= request.text
		soup 				= BeautifulSoup(html, 'html.parser')
		title 				= soup.find("title").text
		Post.comment_title 	= title
		Post.subreddit		= "/r/" + re.search("[a-zA-z]+$", title).group(0)
		self.clearPage()
		
		if request.status_code == 200:
			self.addLabel(title, TITLE_FONT, True)
			
			if not re.search("^http", Post.content_link):
				Post.content_link = DOMAIN + Post.content_link
			
			if Post.content_link == Post.thread_link and not re.search("^self\.", Post.content_domain):
				Post.content_link = soup.select_one("a.title.may-blank")['href']
			elif re.search("^self\.", Post.content_domain):
				self.displaySelfPost(soup)
			
			self.displayComments(soup)
			self.post = Post
		else:
			self.addLabel("Error: Received status code " + str(request.status_code), COMMENT_FONT, False)
			
		self.controller.showFrame(CommentsPage)
		
	def displayComments(self, soup):
		comments = soup.select("div.comment div.entry form.usertext div.usertext-body div.md p")
		if comments:
			for comment in comments:
				self.addLabel(comment.text, COMMENT_FONT, False)
		else:
			self.addLabel("There don't seem to be any comments here", COMMENT_FONT, False)
			
	def displaySelfPost(self, soup):
		self_posts = soup.select("div.self div.entry form.usertext div.usertext-body div.md p")
		for self_post in self_posts:
			self.addLabel(self_post.text, SELF_POST_FONT, False)
		
	def clearPage(self):
		for element in self.list_of_elements:
			element.destroy()
		self.list_of_elements.clear()
	
	def addLabel(self, message, font, title_bind):
		message = TOOLKIT.validateChars(message)
		label = tk.Label(self, text=message, font=font, anchor='w', wraplength=SCREEN_WIDTH, bg=BACKGROUND_COLOUR, fg=FOREGROUND_COLOUR)
		self.list_of_elements.append(label)
		label.pack(fill='both', pady=POST_Y_PADDING)
		
		if title_bind:
			label.bind("<Enter>", lambda x: self.config(cursor="hand2"))
			label.bind("<Leave>", lambda x: self.config(cursor="arrow"))
			label.bind("<Button-1>", lambda x: self.controller.frames[ContentPage].loadContent(self.post))

class ContentPage(tk.Frame):
	list_of_elements = []
	reloaded = False
	
	def __init__(self, parent, controller):
		tk.Frame.__init__(self, parent, bg=BACKGROUND_COLOUR)
		back_button = ttk.Button(self, text="Go back", 
								command=lambda: controller.showFrame(CommentsPage))
		back_button.pack()
		self.controller = controller
		
	def loadContent(self, Post):			# Does not load content created by JavaScript
		url = Post.content_link
		print("Content URL is", url)
		request = requests.get(url, headers=HEADERS)
		html = request.text
		soup = BeautifulSoup(html, 'lxml')
		title = soup.find("title")
		
		if title:
			title = TOOLKIT.validateChars(title.text) + " : " + Post.subreddit
		else:
			title = TOOLKIT.validateChars(Post.comment_title)
			
		Post.checkMediaType()
		
		print("media type is", Post.media_type)
		
		self.clearPage()
		
		if request.status_code == 200:
			self.addWidget(title, MediaType.TEXT, TITLE_FONT)
			self.displayContent(soup, Post)
		else:
			self.addWidget("Error: Received status code " + str(request.status_code), MediaType.TEXT, COMMENT_FONT)
			
#		if re.search("redirected", title) and not self.reloaded:
#			time.sleep(6)
#			self.loadContent(Post)
#			self.reloaded = True
			
		self.controller.showFrame(ContentPage)
		
	def clearPage(self):
		for element in self.list_of_elements:
			element.destroy()
		self.list_of_elements.clear()
		
	def displayContent(self, soup, post):
		if post.media_type == MediaType.TEXT:
			text_contents = soup.select("p")
			for text_content in text_contents:
				self.addWidget(text_content.text, MediaType.TEXT, COMMENT_FONT)
		elif post.media_type == MediaType.IMAGE:
			if post.indirectMediaLink:
				image_contents = soup.find_all("img")
				for image_content in image_contents:
					image_src = image_content['src']
					while re.search("^\/", image_src):
						image_src = TOOLKIT.removePrefix(image_src, "/")
						if not re.search("^\/", image_src):
							image_src = "https://" + image_src
						post.content_link = image_src
			self.addWidget(post.content_link, post.media_type, None)
		elif post.media_type == MediaType.VIDEO:
			pass
		elif post.media_type == MediaType.GIF:
			addWidget(post.content_link, post.media_type, None)
		
	def addWidget(self, content, type, font):
		if type == MediaType.TEXT:
			content = TOOLKIT.validateChars(content)
			label = tk.Label(self, text=content, font=font, anchor='w', wraplength=SCREEN_WIDTH, bg=BACKGROUND_COLOUR, fg=FOREGROUND_COLOUR)
			self.list_of_elements.append(label)
			label.pack(fill='both', pady=POST_Y_PADDING)
		elif type == MediaType.IMAGE or type == MediaType.GIF:
			page 			= urlopen(content)
			picture 		= io.BytesIO(page.read())
			image 			= Image.open(picture)
			tk_image 		= ImageTk.PhotoImage(image)
			shrink_ratio 	= 1
			
			while tk_image.height() > TRUE_SCREEN_HEIGHT or tk_image.width() > TRUE_SCREEN_WIDTH:
				if tk_image.height() > TRUE_SCREEN_HEIGHT and tk_image.width() > TRUE_SCREEN_WIDTH:
					if TRUE_SCREEN_HEIGHT / tk_image.height() > TRUE_SCREEN_WIDTH / tk_image.width():
						shrink_ratio = TRUE_SCREEN_HEIGHT / tk_image.height()
					else:
						shrink_ratio = TRUE_SCREEN_WIDTH / tk_image.width()
				elif tk_image.height() > TRUE_SCREEN_HEIGHT:
					shrink_ratio = TRUE_SCREEN_HEIGHT / tk_image.height()
				else:
					shrink_ratio = TRUE_SCREEN_WIDTH / tk_image.width()
				
				image		= Image.open(picture).resize((round(tk_image.width() * shrink_ratio), round(tk_image.height() * shrink_ratio)))
				tk_image	= ImageTk.PhotoImage(image)
			
			label 			= tk.Label(self, image=tk_image)
			label.image 	= tk_image
			self.list_of_elements.append(label)
			label.pack()
		
class Post:
	def __init__(self, thread_title_label, content_link, thread_link, content_domain, subreddit):
		self.thread_title_label = thread_title_label
		self.content_link 		= content_link
		self.thread_link 		= thread_link
		self.content_domain 	= content_domain
		self.subreddit			= subreddit
		self.comment_title 		= thread_title_label.cget("text")
		self.indirectMediaLink 	= True
		
		
	def checkMediaType(self):
		if (re.search("youtub\.be|gfycat\.com|v\.redd\.it", self.content_domain) 
			or (re.search("imgur\.com", self.content_link))):
			self.media_type = MediaType.VIDEO
		elif re.search("\.gif$|\.gifv$", self.content_link):
			self.media_type = MediaType.GIF
		elif re.search("i\.redd\.it|imgur\.com|instagram\.com|twimg\.com|\.[^\..]{1,5}$", self.content_domain):	#Added a $ here, remove if causing issues
			self.media_type = MediaType.IMAGE
			if re.search("\.[^\..]{1,5}", self.content_link) and not re.search("^\.com$", self.content_link):
				self.indirectMediaLink = False
		else:
			self.media_type = MediaType.TEXT
	
app = Roddit()
app.mainloop()