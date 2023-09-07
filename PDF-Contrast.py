import os
import time
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageEnhance, ImageFile
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError
import img2pdf
from multiprocessing import Pool, cpu_count, Queue, current_process, Manager
import shutil
from PIL import Image, ImageEnhance
ImageFile.LOAD_TRUNCATED_IMAGES = True

class App:
		def __init__(self):
				self.root = tk.Tk()
				self.root.title("PDF Contrast")
				window_width = 600
				window_height = 400
			
				# Get screen width and height
				screen_width = self.root.winfo_screenwidth()
				screen_height = self.root.winfo_screenheight()
			
				# Calculate position for centering the window
				position_top = int(screen_height / 2 - window_height / 2)
				position_right = int(screen_width / 2 - window_width / 2)
			
				# Set the initial size and position of the window
				self.root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')
			
				self.contrast_scale = tk.Scale(self.root, from_=1, to=3, resolution=0.1, length=400,
																				orient=tk.HORIZONTAL, label='Contrast Level')
				self.contrast_scale.set(1.5)
				self.contrast_scale.pack()
			
				# Create a custom style
				style = ttk.Style()
				# Define custom layout
				style.layout('custom.Horizontal.TProgressbar',
											[('Horizontal.Progressbar.trough',
												{'children': [('Horizontal.Progressbar.pbar',
																			{'side': 'left', 'sticky': 'ns'})],
												'sticky': 'nswe'}),
											('Horizontal.Progressbar.label', {'sticky': ''})])
			
				# Configure custom style. 'Horizontal.TProgressbar' is the base style for horizontal progress bars.
				style.configure('custom.Horizontal.TProgressbar', 
							background='#4f98ca',  # Color of the progress bar
							troughcolor='gray',  # Color of the trough (background area of the progress bar)
							thickness=50)  # Height of the progress bar
			
					# Initialize the progress bar with the custom style and maximum value of 100
				self.progress = ttk.Progressbar(self.root, style="custom.Horizontal.TProgressbar", length=400, maximum=100)
			# Create the progress bar with the custom style
				self.progress = ttk.Progressbar(self.root, style="custom.Horizontal.TProgressbar", length=400, maximum=100)  # Initialize with maximum value of 100
			
				self.progress.pack()
				self.status_label = tk.Label(self.root, text='')
				self.status_label.pack()
				self.button_dir = tk.Button(self.root, text="Select Directory", command=self.select_directory)
				self.button_dir.pack()
				self.button_file = tk.Button(self.root, text="Select File", command=self.select_file)
				self.button_file.pack()
			
		def enhance_contrast(self, pdf_file_path, enhanced_images_dir, contrast_level):
			print(f"In enhance_contrast with file {pdf_file_path}")
			"""
			Enhances the contrast of a PDF file and saves the resulting images in a specified directory.
		
			Args:
				pdf_file_path (str): The path of the PDF file.
				enhanced_images_dir (str): The directory to save the enhanced images.
				contrast_level (float): The level of contrast to apply.
		
			Returns:
				list of str: The paths of the enhanced images.
			"""
			# Convert the PDF to a list of images
			images = convert_from_path(pdf_file_path)
			
			# List to hold the paths of the enhanced images
			enhanced_image_paths = []
			
			for i, image in enumerate(images):
				# Enhance the contrast of the image using the contrast_level parameter
				enhancer = ImageEnhance.Contrast(image)
				enhanced_image = enhancer.enhance(contrast_level)
				
				# Save the enhanced image in the 'enhanced_images' directory
				enhanced_image_path = os.path.join(enhanced_images_dir, f"enhanced_{i}.png")
				enhanced_image.save(enhanced_image_path)
				
				# Add the path of the enhanced image to the list
				enhanced_image_paths.append(enhanced_image_path)
				
			return enhanced_image_paths
	
		@staticmethod
		def process_pdf(queue, file_path, contrast_level):
			print(f"In process_pdf with file {file_path}")
			start_time = time.time()
			
			# Convert PDF to images
			try:
				images = convert_from_path(file_path)
			except PDFPageCountError:
				print(f"Unable to process file: {file_path}. Skipping.")
				return
			
			enhanced_images = []
			for i, image in enumerate(images):
				image_path = f'temp_img_{i}.png'
				enhanced_path = f'temp_img_enhanced_{i}.png'
				image.save(image_path)
				
				# Enhance image contrast
				if App().enhance_contrast(image_path, enhanced_path, contrast_level):
					# Append the enhanced image path to the list
					enhanced_images.append(enhanced_path)
					
				# Return the size of the processed file through the queue
				queue.put(os.path.getsize(file_path))
				
		def convert_images_to_pdf(self, enhanced_image_paths, original_pdf_path):
			"""
			Converts a list of images to a single PDF file and saves it in the same location as the original PDF file 
			with "_dark" appended to the original filename.
		
			Args:
				enhanced_image_paths (list of str): The paths of the images to convert.
				original_pdf_path (str): The path of the original PDF file.
			"""
			# Ensure there are images to convert
			if not enhanced_image_paths:
				print("No images to convert to PDF.")
				return
			
			# Create the output filename by appending "_dark" to the original filename
			base_name = os.path.splitext(original_pdf_path)[0]
			output_pdf_path = base_name + "_dark.pdf"
			
			# Convert the images to a PDF
			try:
				print(f"Converting the following images to PDF: {enhanced_image_paths}")
				with open(output_pdf_path, "wb") as f:
					f.write(img2pdf.convert([i for i in enhanced_image_paths if i.endswith(".png")]))
				print(f"Successfully wrote {output_pdf_path}")
			except Exception as e:
				print(f"Failed to convert images to PDF: {e}")
				
				
		def select_directory(self):
			# Open a dialog to select a directory
			dir_path = filedialog.askdirectory()
			
			if dir_path:
				# Get list of all files in the directory
				dir_files = os.listdir(dir_path)
				
				# Filter out non-PDF files
				pdf_files = [file for file in dir_files if file.endswith('.pdf')]
				
				# Calculate total size of all PDF files
				total_size = sum(os.path.getsize(os.path.join(dir_path, file)) for file in pdf_files)
				
				# Create a directory to store the enhanced images
				enhanced_images_dir = os.path.join(dir_path, 'enhanced_images')
				os.makedirs(enhanced_images_dir, exist_ok=True)
				
				processed_size = 0  # Initialize processed size to 0
				
				# Process each PDF file
				for pdf_file in pdf_files:
					# Full path of the PDF file
					pdf_file_path = os.path.join(dir_path, pdf_file)
					
					# Enhance the contrast of the PDF file and save the resulting images in the 'enhanced_images' directory
					try:
						enhanced_image_paths = self.enhance_contrast(pdf_file_path, enhanced_images_dir, self.contrast_scale.get())
					except Exception as e:
						print(f"Failed to enhance contrast for {pdf_file_path}: {e}")
						continue  # Skip to the next PDF file
					
					# Convert the enhanced images to PDF
					try:
						self.convert_images_to_pdf(enhanced_image_paths, pdf_file_path)
					except Exception as e:
						print(f"Failed to convert images to PDF for {pdf_file_path}: {e}")
						continue  # Skip to the next PDF file
					
					# Update processed size and progress bar
					processed_size += os.path.getsize(pdf_file_path)
					self.progress["value"] = (processed_size / total_size) * 100
					self.root.update()  # Update the UI to reflect changes
					
				# Delete the temporary directory after processing all files
				try:
					shutil.rmtree(enhanced_images_dir)
				except Exception as e:
					print(f"Failed to delete directory {enhanced_images_dir}: {e}")
					
		def select_file(self):
			file_path = filedialog.askopenfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
			if file_path:
				total_size = os.path.getsize(file_path)
				with Manager() as manager:
					queue = manager.Queue()
					
					# Create a directory to store the enhanced images
					enhanced_images_dir = os.path.join(os.path.dirname(file_path), 'enhanced_images')
					os.makedirs(enhanced_images_dir, exist_ok=True)
					
					# Enhance the contrast of the PDF file and save the resulting images in the 'enhanced_images' directory
					try:
						enhanced_image_paths = self.enhance_contrast(file_path, enhanced_images_dir, self.contrast_scale.get())
						self.convert_images_to_pdf(enhanced_image_paths, file_path)
					except Exception as e:
						print(f"Failed to enhance contrast for {file_path}: {e}")
						
					# Calculate progress
					with Pool(1) as pool:  # Create a pool with a single worker
						result = pool.apply_async(self.process_pdf, (queue, file_path, self.contrast_scale.get()))
						pool.close()
						pool.join()
					
					file_size = queue.get()
					self.progress["value"] = (file_size / total_size) * 100
					self.root.update()  # Update the UI to reflect changes
					self.status_label['text'] = 'Done'
					try:
						shutil.rmtree(enhanced_images_dir)
					except Exception as e:
						print(f"Failed to delete directory {enhanced_images_dir}: {e}")
					
		def run(self):
			self.root.mainloop()
			
if __name__ == '__main__':
		App().run()
