"""
Desktop Application for Excel/CSV to RAG System
A standalone desktop GUI application (not web-based)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
from pathlib import Path
from datetime import datetime
from excel_to_rag import ExcelToRAG
import threading


class ExcelRAGDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Excel/CSV to RAG System")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f5f7fa')
        
        # Modern color scheme
        self.colors = {
            'primary': '#667eea',
            'primary_dark': '#5568d3',
            'secondary': '#764ba2',
            'success': '#10b981',
            'danger': '#ef4444',
            'warning': '#f59e0b',
            'info': '#3b82f6',
            'bg_main': '#f5f7fa',
            'bg_card': '#ffffff',
            'text_primary': '#1f2937',
            'text_secondary': '#6b7280',
            'border': '#e5e7eb',
            'hover': '#f3f4f6'
        }
        
        # Variables
        self.rag_system = None
        self.current_file = None
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.files_folder_path = os.path.join(os.path.expanduser("~"), "Documents")  # Default folder for Excel files
        self.selected_file_path = None
        self.selected_files = {}  # Dictionary to store selected files: {file_path: checkbox_var}
        self.loaded_files = set()  # Set of already processed files
        
        # Load settings
        self.load_settings()
        
        # Initialize path_var for settings (used in Info window)
        self.path_var = tk.StringVar(value=self.download_path)
        self.files_folder_var = tk.StringVar(value=self.files_folder_path)
        
        # Create UI
        self.create_ui()
        
        # Initialize RAG system
        self.init_rag_system()
        
        # Load file list after UI is created
        self.root.after(100, self.refresh_file_list)
    
    def load_settings(self):
        """Load settings from file."""
        settings_file = "app_settings.json"
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self.download_path = settings.get('download_path', self.download_path)
                    self.files_folder_path = settings.get('files_folder_path', self.files_folder_path)
            except:
                pass
    
    def save_settings(self):
        """Save settings to file."""
        settings_file = "app_settings.json"
        settings = {
            'download_path': self.download_path,
            'files_folder_path': self.files_folder_path
        }
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def init_rag_system(self):
        """Initialize RAG system in background."""
        def init():
            try:
                db_path = os.path.join(os.getcwd(), 'chroma_db')
                self.rag_system = ExcelToRAG(
                    embedding_model="all-MiniLM-L6-v2",
                    db_path=db_path,
                    collection_name="excel_data"
                )
                self.status_label.config(text="Ready - Upload a file to begin", fg=self.colors['success'])
                self.status_dot.config(fg=self.colors['success'])
            except Exception as e:
                self.status_label.config(text=f"Error initializing: {str(e)}", fg=self.colors['danger'])
                self.status_dot.config(fg=self.colors['danger'])
        
        threading.Thread(target=init, daemon=True).start()
        self.status_label.config(text="Initializing system...", fg=self.colors['info'])
        self.status_dot.config(fg=self.colors['info'])
    
    def create_ui(self):
        """Create the user interface."""
        # Modern Header with gradient effect
        header_frame = tk.Frame(self.root, bg=self.colors['primary'], height=100)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        header_content = tk.Frame(header_frame, bg=self.colors['primary'])
        header_content.pack(fill=tk.BOTH, expand=True, padx=30)
        
        title_label = tk.Label(
            header_content,
            text="📊 Excel/CSV to RAG System",
            font=('Segoe UI', 24, 'bold'),
            bg=self.colors['primary'],
            fg='white'
        )
        title_label.pack(side=tk.LEFT, pady=25)
        
        subtitle_label = tk.Label(
            header_content,
            text="AI-Powered Data Query System | SLM-Based | Fully Offline",
            font=('Segoe UI', 10),
            bg=self.colors['primary'],
            fg='#e0e0e0'
        )
        subtitle_label.pack(side=tk.LEFT, padx=(15, 0), pady=25)
        
        # Header buttons (Info only)
        header_buttons = tk.Frame(header_content, bg=self.colors['primary'])
        header_buttons.pack(side=tk.RIGHT, pady=25)
        
        # Info button
        info_btn = tk.Button(
            header_buttons,
            text="ℹ️ Info & Examples",
            command=self.open_info,
            bg='#8b9dc3',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            padx=20,
            pady=10,
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            activebackground='#9fa8c4',
            activeforeground='white'
        )
        info_btn.pack(side=tk.LEFT, padx=5)
        
        # Main container with modern spacing
        main_frame = tk.Frame(self.root, bg=self.colors['bg_main'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Left panel - Upload & Settings (modern card design)
        left_panel = tk.Frame(
            main_frame,
            bg=self.colors['bg_card'],
            relief=tk.FLAT,
            bd=0
        )
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10), pady=0)
        left_panel.config(width=420)
        
        # Add shadow effect border
        shadow_frame = tk.Frame(
            main_frame,
            bg='#e5e7eb',
            height=2
        )
        shadow_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Right panel - Query & Answers (modern card design)
        right_panel = tk.Frame(
            main_frame,
            bg=self.colors['bg_card'],
            relief=tk.FLAT,
            bd=0
        )
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=0)
        
        # Create left panel content
        self.create_left_panel(left_panel)
        
        # Create right panel content
        self.create_right_panel(right_panel)
        
        # Modern Status bar
        status_frame = tk.Frame(self.root, bg='#ffffff', height=40, relief=tk.SOLID, bd=1)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        status_inner = tk.Frame(status_frame, bg='#ffffff')
        status_inner.pack(fill=tk.BOTH, expand=True, padx=15)
        
        self.status_label = tk.Label(
            status_inner,
            text="Initializing system...",
            anchor=tk.W,
            bg='#ffffff',
            fg=self.colors['text_secondary'],
            font=('Segoe UI', 10),
            padx=0
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X)
        
        # Status indicator dot
        self.status_dot = tk.Label(
            status_inner,
            text="●",
            fg=self.colors['info'],
            bg='#ffffff',
            font=('Segoe UI', 12)
        )
        self.status_dot.pack(side=tk.RIGHT, padx=(10, 0))
    
    def create_left_panel(self, parent):
        """Create left panel with file selection from folder."""
        # File selection section - improved spacing
        upload_frame = tk.Frame(parent, bg=self.colors['bg_card'], padx=20, pady=20)
        upload_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(15, 10))
        
        # Section header
        upload_header = tk.Frame(upload_frame, bg=self.colors['bg_card'])
        upload_header.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(
            upload_header,
            text="📁 Select Files from Folder",
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary']
        ).pack(side=tk.LEFT)
        
        # Folder path display
        folder_info_frame = tk.Frame(upload_frame, bg=self.colors['hover'], relief=tk.FLAT, bd=0)
        folder_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.folder_label = tk.Label(
            folder_info_frame,
            text=f"Folder: {self.files_folder_path}",
            bg=self.colors['hover'],
            fg=self.colors['text_secondary'],
            font=('Segoe UI', 9),
            wraplength=360,
            padx=15,
            pady=8,
            justify=tk.LEFT,
            anchor=tk.W
        )
        self.folder_label.pack(fill=tk.X)
        
        # Refresh button
        refresh_btn = tk.Button(
            upload_frame,
            text="🔄 Refresh File List",
            command=self.refresh_file_list,
            bg=self.colors['info'],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            padx=20,
            pady=8,
            cursor='hand2',
            relief=tk.FLAT,
            bd=0,
            activebackground='#2563eb',
            activeforeground='white'
        )
        refresh_btn.pack(pady=(0, 10), fill=tk.X)
        
        # Files list with scrollbar - limit height
        files_list_frame = tk.Frame(upload_frame, bg=self.colors['bg_card'])
        files_list_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        files_list_frame.config(height=200)  # Set a fixed height for file list
        
        # Scrollable canvas for file list
        canvas = tk.Canvas(files_list_frame, bg='white', highlightthickness=1, highlightbackground=self.colors['border'])
        scrollbar = tk.Scrollbar(files_list_frame, orient="vertical", command=canvas.yview)
        self.files_checkbox_frame = tk.Frame(canvas, bg='white')
        
        self.files_checkbox_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.files_checkbox_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        self.files_canvas = canvas
        
        # Select All / Deselect All buttons
        select_buttons_frame = tk.Frame(upload_frame, bg=self.colors['bg_card'])
        select_buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        select_all_btn = tk.Button(
            select_buttons_frame,
            text="✓ Select All",
            command=self.select_all_files,
            bg=self.colors['success'],
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            padx=15,
            pady=6,
            cursor='hand2',
            relief=tk.FLAT,
            bd=0,
            activebackground='#059669',
            activeforeground='white'
        )
        select_all_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        
        deselect_all_btn = tk.Button(
            select_buttons_frame,
            text="✗ Deselect All",
            command=self.deselect_all_files,
            bg=self.colors['danger'],
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            padx=15,
            pady=6,
            cursor='hand2',
            relief=tk.FLAT,
            bd=0,
            activebackground='#dc2626',
            activeforeground='white'
        )
        deselect_all_btn.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        self.process_all_sheets = tk.BooleanVar(value=True)
        check_frame = tk.Frame(upload_frame, bg=self.colors['bg_card'])
        check_frame.pack(fill=tk.X, pady=(0, 10))
        
        sheets_check = tk.Checkbutton(
            check_frame,
            text="Process all sheets (Excel files)",
            variable=self.process_all_sheets,
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary'],
            font=('Segoe UI', 10),
            selectcolor=self.colors['bg_card'],
            activebackground=self.colors['bg_card'],
            activeforeground=self.colors['text_primary']
        )
        sheets_check.pack(side=tk.LEFT)
        
        # Process button with modern styling - larger and more visible
        def on_process_click():
            """Wrapper to ensure button click is registered."""
            print("DEBUG: Process button clicked!")
            self.process_selected_files()
        
        process_btn = tk.Button(
            upload_frame,
            text="⚙️ Process Selected Files",
            command=on_process_click,
            bg=self.colors['success'],
            fg='white',
            font=('Segoe UI', 12, 'bold'),
            padx=30,
            pady=15,
            cursor='hand2',
            state=tk.NORMAL,
            relief=tk.FLAT,
            bd=0,
            activebackground='#059669',
            activeforeground='white'
        )
        process_btn.pack(pady=(0, 10), fill=tk.X)
        self.process_btn = process_btn
        
        # File info with modern text area - larger
        info_label = tk.Label(
            upload_frame,
            text="File Information:",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary'],
            anchor=tk.W
        )
        info_label.pack(anchor=tk.W, pady=(20, 8))
        
        # Create a frame for the text widget with scrollbar - give it proper space
        text_frame = tk.Frame(upload_frame, bg=self.colors['bg_card'])
        text_frame.pack(pady=(0, 20), fill=tk.BOTH, expand=True)
        text_frame.config(height=250)  # Ensure minimum height
        
        self.file_info_text = tk.Text(
            text_frame,
            height=12,
            wrap=tk.WORD,
            bg='white',
            fg=self.colors['text_primary'],
            font=('Segoe UI', 10),
            relief=tk.SOLID,
            bd=1,
            padx=12,
            pady=10,
            highlightthickness=2,
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['primary']
        )
        
        file_info_scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.file_info_text.yview)
        self.file_info_text.configure(yscrollcommand=file_info_scrollbar.set)
        
        self.file_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_right_panel(self, parent):
        """Create right panel with query and answers."""
        # Query section - improved
        query_frame = tk.Frame(parent, bg=self.colors['bg_card'], padx=20, pady=20)
        query_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        # Section header
        query_header = tk.Frame(query_frame, bg=self.colors['bg_card'])
        query_header.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(
            query_header,
            text="❓ Ask Questions",
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary']
        ).pack(side=tk.LEFT)
        
        # Modern input with placeholder effect
        input_frame = tk.Frame(query_frame, bg=self.colors['bg_card'])
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.query_entry = tk.Entry(
            input_frame,
            font=('Segoe UI', 12),
            bg='white',
            fg=self.colors['text_primary'],
            relief=tk.FLAT,
            bd=0,
            highlightthickness=2,
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['primary'],
            insertbackground=self.colors['text_primary']
        )
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 0), pady=0)
        self.query_entry.insert(0, "Type your question here...")
        self.query_entry.config(fg=self.colors['text_secondary'])
        self.query_entry.bind('<FocusIn>', self.on_entry_focus_in)
        self.query_entry.bind('<FocusOut>', self.on_entry_focus_out)
        self.query_entry.bind('<Return>', lambda e: self.submit_query())
        
        query_btn = tk.Button(
            input_frame,
            text="🔍 Ask",
            command=self.submit_query,
            bg=self.colors['primary'],
            fg='white',
            font=('Segoe UI', 12, 'bold'),
            padx=30,
            pady=12,
            cursor='hand2',
            relief=tk.FLAT,
            bd=0,
            activebackground=self.colors['primary_dark'],
            activeforeground='white'
        )
        query_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Modern Answers section - improved
        answers_frame = tk.Frame(parent, bg=self.colors['bg_card'], padx=20, pady=20)
        answers_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        answers_header = tk.Frame(answers_frame, bg=self.colors['bg_card'])
        answers_header.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(
            answers_header,
            text="📋 Answers",
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary']
        ).pack(side=tk.LEFT)
        
        # Answers text area with modern styling
        text_frame = tk.Frame(answers_frame, bg=self.colors['bg_card'])
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.answers_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg='white',
            fg=self.colors['text_primary'],
            padx=15,
            pady=15,
            relief=tk.SOLID,
            bd=1,
            highlightthickness=2,
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['primary'],
            insertbackground=self.colors['text_primary']
        )
        self.answers_text.pack(fill=tk.BOTH, expand=True)
        
        # Modern Download button - larger and more visible
        download_btn = tk.Button(
            answers_frame,
            text="📥 Download Answers",
            command=self.download_answers,
            bg=self.colors['success'],
            fg='white',
            font=('Segoe UI', 12, 'bold'),
            padx=30,
            pady=15,
            cursor='hand2',
            state=tk.DISABLED,
            relief=tk.FLAT,
            bd=0,
            activebackground='#059669',
            activeforeground='white'
        )
        download_btn.pack(fill=tk.X, pady=(10, 0))
        self.download_btn = download_btn
        
        self.current_answers = []
    
    def refresh_file_list(self, preserve_selection=False):
        """Refresh the list of files from the selected folder.
        
        Args:
            preserve_selection: If True, preserve which files were checked before refresh
        """
        if not os.path.exists(self.files_folder_path):
            messagebox.showerror("Error", f"Folder does not exist:\n{self.files_folder_path}")
            return
        
        # Save current selection state if preserving
        saved_selection = set()
        if preserve_selection:
            for file_path, var in self.selected_files.items():
                try:
                    if var.get():
                        saved_selection.add(file_path)
                        print(f"DEBUG: Preserving selection for: {os.path.basename(file_path)}")
                except:
                    pass
        
        # Clear existing checkboxes
        for widget in self.files_checkbox_frame.winfo_children():
            widget.destroy()
        self.selected_files.clear()
        
        # Find all Excel and CSV files
        excel_extensions = ('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv')
        files_found = []
        
        try:
            for file in os.listdir(self.files_folder_path):
                file_path = os.path.join(self.files_folder_path, file)
                if os.path.isfile(file_path) and file.lower().endswith(excel_extensions):
                    files_found.append(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Error reading folder:\n{str(e)}")
            return
        
        if not files_found:
            no_files_label = tk.Label(
                self.files_checkbox_frame,
                text="No Excel/CSV files found in this folder.",
                bg='white',
                fg=self.colors['text_secondary'],
                font=('Segoe UI', 10),
                padx=10,
                pady=10
            )
            no_files_label.pack(anchor=tk.W, padx=10, pady=5)
            return
        
        # Create checkboxes for each file
        for file_path in sorted(files_found):
            file_frame = tk.Frame(self.files_checkbox_frame, bg='white')
            file_frame.pack(fill=tk.X, padx=5, pady=3)
            
            # Restore selection state if preserving
            should_be_checked = preserve_selection and file_path in saved_selection
            var = tk.BooleanVar(value=should_be_checked)
            filename = os.path.basename(file_path)
            
            # Check if file is already loaded
            is_loaded = file_path in self.loaded_files
            checkbox_text = f"✓ {filename}" if is_loaded else filename
            
            checkbox = tk.Checkbutton(
                file_frame,
                text=checkbox_text,
                variable=var,
                bg='white',
                fg=self.colors['text_primary'] if not is_loaded else self.colors['success'],
                font=('Segoe UI', 9),
                selectcolor='white',
                activebackground='white',
                activeforeground=self.colors['text_primary'],
                anchor=tk.W,
                command=lambda fp=file_path, v=var: self._on_file_checkbox_change(fp, v)
            )
            checkbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            if is_loaded:
                loaded_label = tk.Label(
                    file_frame,
                    text="(Loaded)",
                    bg='white',
                    fg=self.colors['success'],
                    font=('Segoe UI', 8, 'italic')
                )
                loaded_label.pack(side=tk.RIGHT, padx=5)
            
            # Store the file path and variable
            self.selected_files[file_path] = var
            if should_be_checked:
                print(f"DEBUG: Restored selection for: {filename}")
        
        # Update canvas scroll region
        self.files_checkbox_frame.update_idletasks()
        self.files_canvas.configure(scrollregion=self.files_canvas.bbox("all"))
        
        # Update folder label
        self.folder_label.config(text=f"Folder: {self.files_folder_path}\n({len(files_found)} files found)")
    
    def select_all_files(self):
        """Select all files in the list."""
        for var in self.selected_files.values():
            var.set(True)
    
    def deselect_all_files(self):
        """Deselect all files in the list."""
        for var in self.selected_files.values():
            var.set(False)
    
    def _on_file_checkbox_change(self, file_path, var):
        """Debug callback when checkbox is clicked."""
        filename = os.path.basename(file_path)
        is_checked = var.get()
        print(f"DEBUG: Checkbox changed for {filename}: {'checked' if is_checked else 'unchecked'}")
    
    def process_selected_files(self):
        """Process all selected files."""
        print("="*50)
        print("DEBUG: process_selected_files called")
        print(f"DEBUG: Total files in selected_files dict: {len(self.selected_files)}")
        
        if len(self.selected_files) == 0:
            messagebox.showwarning("No Files Found", 
                f"No files found in the selected folder.\n\n"
                f"Folder: {self.files_folder_path}\n\n"
                f"Please:\n"
                f"1. Click the Info button (ℹ️)\n"
                f"2. Go to Settings tab\n"
                f"3. Set the 'Excel Files Folder Path' to a folder containing Excel/CSV files\n"
                f"4. Click 'Refresh File List' button")
            return
        
        # Get selected files
        selected = []
        for path, var in self.selected_files.items():
            try:
                checkbox_value = var.get()
                filename = os.path.basename(path)
                print(f"DEBUG: File '{filename}' checkbox value: {checkbox_value}")
                if checkbox_value:
                    selected.append(path)
                    print(f"DEBUG: ✓ File selected: {filename}")
            except Exception as e:
                print(f"DEBUG: ✗ Error checking checkbox for {path}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"DEBUG: Total selected files: {len(selected)}")
        print("="*50)
        
        if not selected:
            file_list = "\n".join([f"  • {os.path.basename(path)}" for path in list(self.selected_files.keys())[:10]])
            if len(self.selected_files) > 10:
                file_list += f"\n  ... and {len(self.selected_files) - 10} more files"
            
            messagebox.showwarning("No Files Selected", 
                f"Please select at least one file to process.\n\n"
                f"Found {len(self.selected_files)} files in folder:\n"
                f"{file_list}\n\n"
                f"✓ Check the boxes next to the files you want to process\n"
                f"✓ Then click 'Process Selected Files' again")
            return
        
        if not self.rag_system:
            messagebox.showerror("Error", "System not initialized yet. Please wait...")
            return
        
        # Disable button immediately
        self.process_btn.config(state=tk.DISABLED)
        self.status_label.config(text=f"Processing {len(selected)} file(s)...", fg=self.colors['info'])
        self.status_dot.config(fg=self.colors['info'])
        self.file_info_text.delete(1.0, tk.END)
        self.file_info_text.insert(1.0, f"Processing {len(selected)} file(s)...\nPlease wait...\n\n")
        
        def process():
            try:
                print(f"DEBUG: Starting processing thread for {len(selected)} files")
                process_all = self.process_all_sheets.get()
                info_text = f"Processing {len(selected)} file(s)...\n\n"
                total_processed = 0
                
                for idx, file_path in enumerate(selected):
                    try:
                        filename = os.path.basename(file_path)
                        print(f"DEBUG: Processing file {idx+1}/{len(selected)}: {filename}")
                        info_text += f"📄 [{idx+1}/{len(selected)}] {filename}\n"
                        
                        # Update progress in UI
                        progress_text = f"Processing file {idx+1}/{len(selected)}: {filename}...\n\n"
                        self.root.after(0, lambda t=progress_text: self._update_file_info(t))
                        
                        # Check if file exists
                        if not os.path.exists(file_path):
                            raise FileNotFoundError(f"File not found: {file_path}")
                        
                        if process_all and file_path.lower().endswith(('.xlsx', '.xls', '.xlsm', '.xlsb')):
                            # Process all sheets
                            print(f"DEBUG: Reading all sheets from {filename}")
                            sheets_dict = self.rag_system.read_all_sheets(file_path)
                            info_text += f"   Sheets: {len(sheets_dict)}\n"
                            print(f"DEBUG: Found {len(sheets_dict)} sheets")
                            
                            for sheet_name, df in sheets_dict.items():
                                print(f"DEBUG: Processing sheet '{sheet_name}' with {len(df)} rows")
                                md_content = self.rag_system.convert_to_markdown(df, metadata={'sheet_name': sheet_name, 'file_path': file_path})
                                chunks = self.rag_system.chunk_markdown(md_content)
                                print(f"DEBUG: Created {len(chunks)} chunks for sheet '{sheet_name}'")
                                sheet_file_id = f"{Path(file_path).stem}_{sheet_name}"
                                self.rag_system.embed_and_store(chunks, file_id=sheet_file_id)
                                print(f"DEBUG: Stored chunks for sheet '{sheet_name}'")
                                info_text += f"   - '{sheet_name}': {len(df)} rows, {len(df.columns)} columns\n"
                        else:
                            # Process single sheet/file
                            print(f"DEBUG: Reading single sheet/file: {filename}")
                            df = self.rag_system.read_file(file_path)
                            print(f"DEBUG: Read DataFrame with {len(df)} rows, {len(df.columns)} columns")
                            md_content = self.rag_system.convert_to_markdown(df, metadata={'file_path': file_path})
                            chunks = self.rag_system.chunk_markdown(md_content)
                            print(f"DEBUG: Created {len(chunks)} chunks")
                            file_id = Path(file_path).stem
                            self.rag_system.embed_and_store(chunks, file_id=file_id)
                            print(f"DEBUG: Stored chunks for file {filename}")
                            info_text += f"   Rows: {len(df)}, Columns: {len(df.columns)}\n"
                        
                        # Verify data was actually stored
                        try:
                            # Check if chunks were stored by querying the database
                            test_query = self.rag_system.collection.get()
                            stored_count = len(test_query['ids']) if test_query['ids'] else 0
                            print(f"DEBUG: Total chunks in database after processing: {stored_count}")
                            
                            if stored_count == 0 and idx == 0:
                                # First file and no data - something went wrong
                                raise Exception("No data was stored in database. Embedding may have failed.")
                        except Exception as verify_error:
                            print(f"DEBUG: Verification error (non-critical): {verify_error}")
                        
                        self.loaded_files.add(file_path)
                        total_processed += 1
                        info_text += "   ✓ Processed successfully\n\n"
                        print(f"DEBUG: ✓ Successfully processed {filename}")
                        
                        # Show success message for first file
                        if idx == 0:
                            self.root.after(0, lambda fn=filename: messagebox.showinfo(
                                "Processing Started", 
                                f"Processing started for: {fn}\n\n"
                                f"Check the File Information section for progress.\n"
                                f"You can ask questions once processing completes."
                            ))
                        
                    except Exception as e:
                        error_msg = str(e)
                        info_text += f"   ✗ Error: {error_msg}\n\n"
                        print(f"ERROR processing {file_path}: {error_msg}")  # Debug print
                        import traceback
                        traceback.print_exc()
                        # Show error in UI
                        self.root.after(0, lambda msg=error_msg, fn=filename: messagebox.showerror(
                            "Processing Error", 
                            f"Error processing file: {fn}\n\n{msg}\n\nCheck console for details."
                        ))
                
                info_text += f"\n✅ Total: {total_processed}/{len(selected)} files processed successfully"
                print(f"DEBUG: Processing complete. {total_processed}/{len(selected)} files processed")
                
                # Verify final database state
                try:
                    final_data = self.rag_system.collection.get()
                    final_count = len(final_data['ids']) if final_data['ids'] else 0
                    info_text += f"\n📊 Total chunks in database: {final_count}"
                    print(f"DEBUG: Final database state: {final_count} chunks stored")
                except Exception as e:
                    print(f"DEBUG: Error checking final database state: {e}")
                
                # Update UI with final results
                self.root.after(0, lambda t=info_text: self._update_file_info(t))
                # Refresh file list but preserve current selection
                self.root.after(0, lambda: self.refresh_file_list(preserve_selection=True))
                self.root.after(0, lambda: self.status_label.config(text=f"Files processed: {total_processed}/{len(selected)} - Ready for queries!", fg='green'))
                self.root.after(0, lambda: self.status_dot.config(fg='green'))
                self.root.after(0, lambda: self.process_btn.config(state=tk.NORMAL))
                
                # Show completion message
                if total_processed > 0:
                    self.root.after(0, lambda tp=total_processed, ts=len(selected): messagebox.showinfo(
                        "Processing Complete", 
                        f"✅ Successfully processed {tp}/{ts} file(s)!\n\n"
                        f"You can now ask questions about your data."
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showwarning(
                        "No Files Processed", 
                        "No files were successfully processed.\n\nCheck the File Information section for error details."
                    ))
                
            except Exception as e:
                error_msg = str(e)
                print(f"CRITICAL ERROR in processing thread: {error_msg}")  # Debug print
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Critical Error", f"Processing failed:\n{msg}\n\nCheck console for details."))
                self.root.after(0, lambda msg=error_msg: self.status_label.config(text=f"Error: {msg[:50]}...", fg='red'))
                self.root.after(0, lambda: self.status_dot.config(fg='red'))
                self.root.after(0, lambda: self.process_btn.config(state=tk.NORMAL))
        
        print(f"DEBUG: Starting processing thread...")
        thread = threading.Thread(target=process, daemon=True)
        thread.start()
        print(f"DEBUG: Thread started: {thread.is_alive()}")
    
    def _update_file_info(self, text):
        """Helper method to update file info text widget."""
        self.file_info_text.delete(1.0, tk.END)
        self.file_info_text.insert(1.0, text)
    
    def process_file(self):
        """Process the selected file."""
        if not self.selected_file_path:
            messagebox.showwarning("No File", "Please select a file first")
            return
        
        if not self.rag_system:
            messagebox.showerror("Error", "System not initialized yet. Please wait...")
            return
        
        def process():
            try:
                self.status_label.config(text="Processing file...", fg=self.colors['info'])
                self.status_dot.config(fg=self.colors['info'])
                self.process_btn.config(state=tk.DISABLED)
                
                process_all = self.process_all_sheets.get()
                
                if process_all and self.selected_file_path.lower().endswith(('.xlsx', '.xls', '.xlsm')):
                    # Process all sheets
                    sheets_dict = self.rag_system.read_all_sheets(self.selected_file_path)
                    info_text = f"File: {os.path.basename(self.selected_file_path)}\n"
                    info_text += f"Total Sheets: {len(sheets_dict)}\n\n"
                    
                    for sheet_name, df in sheets_dict.items():
                        md_content = self.rag_system.convert_to_markdown(df, metadata={'sheet_name': sheet_name})
                        chunks = self.rag_system.chunk_markdown(md_content)
                        sheet_file_id = f"{Path(self.selected_file_path).stem}_{sheet_name}"
                        self.rag_system.embed_and_store(chunks, file_id=sheet_file_id)
                        info_text += f"Sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns\n"
                    
                    self.file_info_text.delete(1.0, tk.END)
                    self.file_info_text.insert(1.0, info_text)
                else:
                    # Process single sheet
                    md_path = self.rag_system.process_file(
                        self.selected_file_path,
                        save_md=False
                    )
                    df = self.rag_system.read_file(self.selected_file_path)
                    
                    info_text = f"File: {os.path.basename(self.selected_file_path)}\n"
                    info_text += f"Rows: {len(df)}\n"
                    info_text += f"Columns: {len(df.columns)}\n"
                    info_text += f"Status: Processed successfully!"
                    
                    self.file_info_text.delete(1.0, tk.END)
                    self.file_info_text.insert(1.0, info_text)
                
                self.current_file = self.selected_file_path
                self.status_label.config(text="File processed successfully! You can now ask questions.", fg=self.colors['success'])
                self.status_dot.config(fg=self.colors['success'])
                messagebox.showinfo("Success", "File processed successfully!")
                
            except Exception as e:
                self.status_label.config(text=f"Error: {str(e)}", fg='red')
                messagebox.showerror("Error", f"Failed to process file:\n{str(e)}")
            finally:
                self.process_btn.config(state=tk.NORMAL)
        
        threading.Thread(target=process, daemon=True).start()
    
    def submit_query(self):
        """Submit a query."""
        query = self.query_entry.get().strip()
        
        if not query:
            messagebox.showwarning("Empty Query", "Please enter a question")
            return
        
        if not self.rag_system:
            messagebox.showerror("Error", "System not initialized")
            return
        
        # Check if any files have been processed (either via current_file or loaded_files)
        if not self.current_file and len(self.loaded_files) == 0:
            messagebox.showwarning("No File Processed", 
                "Please process at least one file first.\n\n"
                "1. Select files using checkboxes\n"
                "2. Click 'Process Selected Files'\n"
                "3. Wait for processing to complete")
            return
        
        # Verify database has data
        try:
            # Quick check: try to get count from collection
            all_data = self.rag_system.collection.get()
            if not all_data['ids'] or len(all_data['ids']) == 0:
                messagebox.showwarning("No Data in Database", 
                    "Files appear to be processed, but no data found in database.\n\n"
                    "Please process files again. Check console for errors.")
                return
        except Exception as e:
            print(f"DEBUG: Error checking database: {e}")
            # Continue anyway - might still work
        
        def query_thread():
            try:
                self.root.after(0, lambda: self.status_label.config(text="Searching...", fg='blue'))
                self.root.after(0, lambda: self.status_dot.config(fg='blue'))
                print(f"DEBUG: Executing query: {query}")
                results = self.rag_system.query(query, n_results=5)
                print(f"DEBUG: Query returned {len(results)} results")
                
                # Try to extract numeric value
                numeric_value = None
                try:
                    numeric_value = self.rag_system.extract_numeric_value(query)
                except:
                    pass
                
                # Display results
                if not results or len(results) == 0:
                    print(f"DEBUG: Query returned no results")
                    # Check if database has any data
                    try:
                        all_data = self.rag_system.collection.get()
                        db_count = len(all_data['ids']) if all_data['ids'] else 0
                        print(f"DEBUG: Database has {db_count} chunks")
                        if db_count == 0:
                            self.root.after(0, lambda: messagebox.showwarning(
                                "No Data Found", 
                                "The database appears to be empty.\n\n"
                                "Please process files again. The embedding may have failed."
                            ))
                    except Exception as db_check_error:
                        print(f"DEBUG: Error checking database: {db_check_error}")
                
                self.root.after(0, lambda: self.display_results(query, results, numeric_value))
                self.root.after(0, lambda: self.status_label.config(text="Query completed", fg='green'))
                self.root.after(0, lambda: self.status_dot.config(fg='green'))
                
            except Exception as e:
                error_msg = str(e)
                print(f"DEBUG: Query error: {error_msg}")
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Query Error", f"Query failed:\n{msg}\n\nCheck console for details."))
                self.root.after(0, lambda msg=error_msg: self.status_label.config(text=f"Error: {msg[:50]}...", fg='red'))
                self.root.after(0, lambda: self.status_dot.config(fg='red'))
        
        threading.Thread(target=query_thread, daemon=True).start()
    
    def display_results(self, query, results, numeric_value):
        """Display query results in a clean, formatted way."""
        self.answers_text.delete(1.0, tk.END)
        
        # Clean header
        output = f"Query: {query}\n"
        output += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        output += f"{'─'*70}\n\n"
        
        # Show extracted numeric value prominently if available
        if numeric_value is not None:
            output += f"📊 Extracted Value: {numeric_value}\n\n"
            output += f"{'─'*70}\n\n"
        
        if not results:
            output += "❌ No results found. Try a different question or check your query.\n"
        else:
            # Detect calculation queries
            query_lower = query.lower()
            is_calculation_query = any(phrase in query_lower for phrase in [
                'cost per unit', 'cost per', 'per unit', 'ratio', 'efficiency',
                'per weight', 'per volume', 'per case'
            ])
            
            # Try to calculate answer for calculation queries
            calculated_answer = None
            if is_calculation_query:
                calculated_answer = self._calculate_answer_from_results(query, results)
            
            # Show calculated answer prominently if available
            if calculated_answer:
                output += f"💡 Answer:\n\n{calculated_answer}\n\n"
                output += f"{'═'*80}\n\n"
            elif numeric_value is not None:
                output += f"📊 Answer: {numeric_value}\n\n"
                output += f"{'─'*80}\n\n"
            
            # Filter and show only most relevant results (max 2)
            if not calculated_answer:
                relevant_results = self._filter_relevant_results(results, query, max_results=2)
                if relevant_results:
                    output += f"📊 Supporting Data:\n\n"
                    for i, result in enumerate(relevant_results, 1):
                        content = self.clean_markdown_content(result["content"])
                        if len(content.strip()) > 50:
                            output += f"{'─'*80}\n"
                            output += f"{content}\n\n"
        
        self.answers_text.insert(1.0, output)
        self.current_answers = results
        self.current_query = query
        self.download_btn.config(state=tk.NORMAL)
    
    def _calculate_answer_from_results(self, query, results):
        """Calculate answer for calculation queries like 'cost per unit weight'."""
        query_lower = query.lower()
        
        # Get more results for better data extraction
        all_results = self.rag_system.query(query, n_results=20)
        
        # Extract data from table rows
        consignment_data = {}
        header_found = False
        col_indices = {}
        
        for result in all_results:
            content = result["content"]
            lines = content.split('\n')
            
            for line in lines:
                if '|' not in line:
                    continue
                
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) < 5:
                    continue
                
                # Check if this is a header row
                if any(keyword in ' '.join(parts).lower() for keyword in ['consignment', 'cost', 'weight', 'volume']):
                    header_found = True
                    # Map column names to indices
                    for idx, part in enumerate(parts):
                        part_lower = part.strip('`').lower()
                        if 'consignment' in part_lower and 'no' in part_lower:
                            col_indices['consignment'] = idx
                        elif 'transportation cost' in part_lower or ('cost' in part_lower and 'rs' in part_lower):
                            col_indices['cost'] = idx
                        elif 'total weight' in part_lower and '%' not in part_lower:
                            col_indices['weight'] = idx
                        elif 'total volume' in part_lower and '%' not in part_lower:
                            col_indices['volume'] = idx
                    continue
                
                # Parse data rows
                if header_found and len(parts) >= max(col_indices.values(), default=0) + 1:
                    try:
                        consignment_no = None
                        cost = None
                        weight = None
                        volume = None
                        
                        # Extract values using column indices
                        if 'consignment' in col_indices:
                            try:
                                consignment_no = int(float(parts[col_indices['consignment']]))
                            except:
                                pass
                        
                        if 'cost' in col_indices:
                            try:
                                cost_str = parts[col_indices['cost']].replace(',', '').replace('₹', '').replace('Rs', '').strip()
                                cost = float(cost_str)
                            except:
                                pass
                        
                        if 'weight' in col_indices:
                            try:
                                weight_str = parts[col_indices['weight']].replace(',', '').replace('kg', '').strip()
                                weight = float(weight_str)
                            except:
                                pass
                        
                        if 'volume' in col_indices:
                            try:
                                volume_str = parts[col_indices['volume']].replace(',', '').replace('m³', '').strip()
                                volume = float(volume_str)
                            except:
                                pass
                        
                        # Calculate based on query type
                        if consignment_no and cost is not None:
                            if ('cost per unit weight' in query_lower or 'cost per weight' in query_lower) and weight and weight > 0:
                                if consignment_no not in consignment_data:
                                    consignment_data[consignment_no] = {
                                        'cost': cost,
                                        'weight': weight,
                                        'cost_per_weight': cost / weight
                                    }
                            elif ('cost per unit volume' in query_lower or 'cost per volume' in query_lower) and volume and volume > 0:
                                if consignment_no not in consignment_data:
                                    consignment_data[consignment_no] = {
                                        'cost': cost,
                                        'volume': volume,
                                        'cost_per_volume': cost / volume
                                    }
                    except Exception as e:
                        continue
        
        # Format answer
        if consignment_data:
            answer = ""
            if 'cost per unit weight' in query_lower or 'cost per weight' in query_lower:
                answer += "💰 Cost per Unit Weight for Each Consignment:\n\n"
                answer += "| Consignment No | Total Cost (Rs) | Total Weight (kg) | Cost per Weight (Rs/kg) |\n"
                answer += "|:---------------|:----------------|:------------------|:------------------------|\n"
                for cons_no in sorted(consignment_data.keys()):
                    data = consignment_data[cons_no]
                    answer += f"| {cons_no} | ₹{data['cost']:,.2f} | {data['weight']:,.2f} | ₹{data['cost_per_weight']:,.4f} |\n"
            elif 'cost per unit volume' in query_lower or 'cost per volume' in query_lower:
                answer += "💰 Cost per Unit Volume for Each Consignment:\n\n"
                answer += "| Consignment No | Total Cost (Rs) | Total Volume (m³) | Cost per Volume (Rs/m³) |\n"
                answer += "|:---------------|:----------------|:------------------|:------------------------|\n"
                for cons_no in sorted(consignment_data.keys()):
                    data = consignment_data[cons_no]
                    answer += f"| {cons_no} | ₹{data['cost']:,.2f} | {data['volume']:,.2f} | ₹{data['cost_per_volume']:,.4f} |\n"
            
            return answer
        
        return None
    
    def _filter_relevant_results(self, results, query, max_results=3):
        """Filter results to show only the most relevant ones."""
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        scored_results = []
        for result in results:
            content_lower = result["content"].lower()
            score = 0
            
            # Score based on keyword matches
            for keyword in query_keywords:
                if len(keyword) > 3:  # Ignore short words
                    score += content_lower.count(keyword)
            
            # Prefer table results over metadata
            if '|' in result["content"] and '---' in result["content"]:
                score += 10
            
            # Prefer actual data over descriptions
            if any(word in content_lower for word in ['row', 'consignment', 'cost', 'weight', 'volume']):
                score += 5
            
            scored_results.append((score, result))
        
        # Sort by score and return top results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [result for score, result in scored_results[:max_results]]
    
    def _clean_markdown_content(self, content):
        """Clean and format markdown content for better readability."""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove numpy type annotations
            line = re.sub(r'np\.float64\(([^)]+)\)', r'\1', line)
            line = re.sub(r'np\.int64\(([^)]+)\)', r'\1', line)
            
            # Remove excessive separators
            if line.strip().startswith('=') and len(line.strip()) > 50:
                continue
            
            # Keep the line
            cleaned_lines.append(line)
        
        cleaned = '\n'.join(cleaned_lines)
        
        # Remove excessive newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()
        
        self.answers_text.insert(1.0, output)
        self.current_answers = results
        self.current_query = query
        self.download_btn.config(state=tk.NORMAL)
    
    def clean_markdown_content(self, content):
        """Clean and format markdown content for better readability."""
        import re
        
        # Remove excessive separators first
        content = re.sub(r'={20,}', '', content)
        content = re.sub(r'-{20,}', '', content)
        
        lines = content.split('\n')
        cleaned_lines = []
        seen_sections = set()
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_stripped = line.strip()
            
            # Skip empty lines at start
            if not cleaned_lines and not line_stripped:
                i += 1
                continue
            
            # Skip excessive separators
            if line_stripped.startswith('=') or (line_stripped.startswith('-') and len(line_stripped) > 15):
                i += 1
                continue
            
            # Remove "Answer X:" labels
            if re.match(r'^Answer\s+\d+:', line_stripped):
                i += 1
                continue
            
            # Handle section headers - show once
            if line_stripped.startswith('##'):
                section_name = line_stripped.replace('#', '').strip()
                if section_name and section_name not in seen_sections:
                    if section_name == 'Column Information':
                        cleaned_lines.append("\n📊 Column Names & Types:\n")
                    elif section_name == 'Complete Table View':
                        cleaned_lines.append("\n📋 Data Table:\n")
                    elif section_name == 'Numeric Summary Statistics':
                        cleaned_lines.append("\n📈 Statistics:\n")
                    elif section_name == 'Data Preview':
                        cleaned_lines.append("\n👀 Preview:\n")
                    else:
                        cleaned_lines.append(f"\n📌 {section_name}\n")
                    seen_sections.add(section_name)
                i += 1
                continue
            
            # Skip section descriptions
            if 'Each row is presented' in line_stripped or 'with its index' in line_stripped:
                i += 1
                continue
            
            # Handle tables - clean up numpy types
            if '|' in line:
                # Clean up numpy type annotations
                line = re.sub(r'np\.float64\(([^)]+)\)', r'\1', line)
                line = re.sub(r'np\.int64\(([^)]+)\)', r'\1', line)
                
                # Keep table structure
                cleaned_lines.append(line)
                i += 1
                continue
            
            # Clean row headers
            if line_stripped.startswith('### Row'):
                row_num = line_stripped.replace('### Row', '').strip()
                if row_num:
                    cleaned_lines.append(f"\n📍 Row {row_num}:\n")
                i += 1
                continue
            
            # Keep meaningful content
            if line_stripped and len(line_stripped) > 2:
                cleaned_lines.append(line_stripped)
            
            i += 1
        
        # Join and clean
        cleaned = '\n'.join(cleaned_lines)
        
        # Remove excessive newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        # Limit length for readability
        if len(cleaned) > 3000:
            lines_list = cleaned.split('\n')
            # Keep first 60 lines or first table
            table_start = None
            for idx, l in enumerate(lines_list):
                if '|' in l and '---' not in l and table_start is None:
                    table_start = max(0, idx - 2)
                    break
            
            if table_start:
                cleaned = '\n'.join(lines_list[:min(table_start + 30, len(lines_list))])
            else:
                cleaned = '\n'.join(lines_list[:60])
            
            cleaned += f"\n\n... (content truncated for readability)\n"
            cleaned += f"💡 Tip: Ask more specific questions for targeted results."
        
        return cleaned
    
    def download_answers(self):
        """Download answers to file."""
        if not self.current_answers:
            messagebox.showwarning("No Answers", "No answers to download")
            return
        
        # Get path from entry field (user might have typed it)
        download_path = self.path_var.get().strip()
        if not download_path:
            download_path = self.download_path
        
        # Validate path
        if not os.path.exists(download_path):
            response = messagebox.askyesno(
                "Path Not Found",
                f"The path '{download_path}' does not exist.\n\n"
                "Would you like to create it or select a different path?"
            )
            if response:
                # Let user select a new path
                new_path = filedialog.askdirectory(title="Select Download Folder")
                if new_path:
                    download_path = new_path
                    self.download_path = new_path
                    self.path_var.set(new_path)
                    self.save_settings()
                else:
                    return  # User cancelled
            else:
                return  # User cancelled
        
        content = self.answers_text.get(1.0, tk.END)
        
        filename = f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(download_path, filename)
        
        try:
            os.makedirs(download_path, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Success", f"✅ File saved successfully!\n\nLocation:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
    
    def browse_download_path(self):
        """Browse for download path."""
        # Get current path from entry if user typed it
        current_path = self.path_var.get()
        if current_path and os.path.exists(current_path):
            initial_dir = current_path
        else:
            initial_dir = self.download_path
        
        path = filedialog.askdirectory(initialdir=initial_dir, title="Select Download Folder")
        if path:
            self.download_path = path
            self.path_var.set(path)
            self.save_settings()
            messagebox.showinfo("Path Updated", f"Download path set to:\n{path}")
    
    def on_entry_focus_in(self, event):
        """Handle focus in on query entry."""
        if self.query_entry.get() == "Type your question here...":
            self.query_entry.delete(0, tk.END)
            self.query_entry.config(fg=self.colors['text_primary'])
    
    def on_entry_focus_out(self, event):
        """Handle focus out on query entry."""
        if not self.query_entry.get():
            self.query_entry.insert(0, "Type your question here...")
            self.query_entry.config(fg=self.colors['text_secondary'])
    
    def insert_example(self, example):
        """Insert example question into query entry."""
        self.query_entry.delete(0, tk.END)
        self.query_entry.insert(0, example)
        self.query_entry.config(fg=self.colors['text_primary'])
        self.query_entry.focus()
    
    def open_settings(self):
        """Open settings window."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("⚙️ Settings")
        settings_window.geometry("500x400")
        settings_window.configure(bg=self.colors['bg_card'])
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Center the window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (400 // 2)
        settings_window.geometry(f"500x400+{x}+{y}")
        
        # Title
        title_frame = tk.Frame(settings_window, bg=self.colors['primary'], height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="⚙️ Settings",
            font=('Segoe UI', 18, 'bold'),
            bg=self.colors['primary'],
            fg='white'
        ).pack(pady=15)
        
        # Content
        content_frame = tk.Frame(settings_window, bg=self.colors['bg_card'], padx=30, pady=30)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Download Path
        tk.Label(
            content_frame,
            text="Download Path:",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary'],
            anchor=tk.W
        ).pack(anchor=tk.W, pady=(0, 10))
        
        path_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
        path_frame.pack(fill=tk.X, pady=(0, 20))
        
        path_var = tk.StringVar(value=self.download_path)
        path_entry = tk.Entry(
            path_frame,
            textvariable=path_var,
            font=('Segoe UI', 10),
            bg='white',
            fg=self.colors['text_primary'],
            relief=tk.FLAT,
            bd=0,
            highlightthickness=2,
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['primary'],
            padx=12,
            pady=10
        )
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = tk.Button(
            path_frame,
            text="Browse",
            command=lambda: self.browse_path_in_settings(path_var, path_entry),
            bg=self.colors['primary'],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            padx=20,
            pady=10,
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            activebackground=self.colors['primary_dark'],
            activeforeground='white'
        )
        browse_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # System Info
        info_frame = tk.LabelFrame(
            content_frame,
            text="System Information",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary'],
            padx=15,
            pady=15
        )
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        info_text = """Technology: Small Language Model (SLM)
Model: Sentence Transformers (all-MiniLM-L6-v2)
Offline: ✅ Fully Offline (No Internet Required)
ML Algorithms: ✅ Yes (Embeddings, Vector Search)
Multiple Files: ✅ Supported
Multiple Sheets: ✅ Supported"""
        
        tk.Label(
            info_frame,
            text=info_text,
            font=('Segoe UI', 9),
            bg=self.colors['bg_card'],
            fg=self.colors['text_secondary'],
            justify=tk.LEFT,
            anchor=tk.W
        ).pack(anchor=tk.W)
        
        # Save button
        save_btn = tk.Button(
            content_frame,
            text="💾 Save Settings",
            command=lambda: self.save_settings_from_window(path_var.get(), settings_window),
            bg=self.colors['success'],
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            padx=25,
            pady=12,
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            activebackground='#059669',
            activeforeground='white'
        )
        save_btn.pack(pady=(20, 0), fill=tk.X)
    
    def browse_path_in_settings(self, path_var, path_entry):
        """Browse for path in settings window."""
        path = filedialog.askdirectory(initialdir=self.download_path)
        if path:
            path_var.set(path)
    
    def save_settings_from_window(self, new_path, window):
        """Save settings from settings window."""
        if new_path and os.path.isdir(new_path):
            self.download_path = new_path
            self.path_var.set(new_path)
            self.save_settings()
            messagebox.showinfo("Success", "Settings saved successfully!")
            window.destroy()
        else:
            messagebox.showerror("Error", "Invalid path. Please select a valid directory.")
    
    def open_info(self):
        """Open info window with tabs: Example Questions, System Info, and Settings."""
        info_window = tk.Toplevel(self.root)
        info_window.title("ℹ️ Information & Settings")
        info_window.geometry("800x700")
        info_window.configure(bg=self.colors['bg_card'])
        info_window.transient(self.root)
        info_window.grab_set()  # Make it modal
        
        # Store reference to info window so we can close it
        self.info_window = info_window
        
        # Center the window
        info_window.update_idletasks()
        x = (info_window.winfo_screenwidth() // 2) - (800 // 2)
        y = (info_window.winfo_screenheight() // 2) - (700 // 2)
        info_window.geometry(f"800x700+{x}+{y}")
        
        # Title
        title_frame = tk.Frame(info_window, bg=self.colors['info'], height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="ℹ️ Information & Settings",
            font=('Segoe UI', 18, 'bold'),
            bg=self.colors['info'],
            fg='white'
        ).pack(pady=15)
        
        # Content with notebook (3 tabs)
        notebook = ttk.Notebook(info_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # ========== TAB 1: Example Questions ==========
        examples_frame = tk.Frame(notebook, bg=self.colors['bg_card'])
        notebook.add(examples_frame, text="📝 Example Questions")
        
        # Create scrollable canvas with proper scrolling
        canvas_frame = tk.Frame(examples_frame, bg=self.colors['bg_card'])
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        canvas = tk.Canvas(canvas_frame, bg=self.colors['bg_card'], highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.colors['bg_card'])
        
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scroll_frame.bind("<Configure>", configure_scroll_region)
        
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        
        def configure_canvas_width(event):
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        canvas.bind('<Configure>', configure_canvas_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Also bind to the canvas itself
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Header
        header_label = tk.Label(
            scroll_frame,
            text="💡 Example Questions - Logistics Optimization",
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary'],
            anchor=tk.W
        )
        header_label.pack(anchor=tk.W, pady=(0, 10))
        
        info_label = tk.Label(
            scroll_frame,
            text="Questions are categorized by complexity. Click any question to use it.\nYou can also ask your own questions - the system will find accurate answers!",
            font=('Segoe UI', 9),
            bg=self.colors['bg_card'],
            fg=self.colors['text_secondary'],
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=500
        )
        info_label.pack(anchor=tk.W, pady=(0, 15), padx=5)
        
        # Categorized FAQs for Logistics Optimization Results
        # Normal Level Questions
        normal_label = tk.Label(
            scroll_frame,
            text="🟢 Normal Level Questions",
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['success'],
            anchor=tk.W
        )
        normal_label.pack(anchor=tk.W, pady=(0, 8), padx=5)
        
        normal_examples = [
                "What are all the column names in this file?",
                "How many consignments are there in total?",
                "What is the total number of rows?",
                "Show me the first 5 rows of data",
                "What are all the source locations?",
                "What are all the destination locations?",
                "What products are being shipped?",
                "What are the different transportation modes used?",
                "What is the date range for dispatch dates?",
                "What is the date range for expected arrival dates?",
                "How many unique customers are there?",
                "What are the different load types?",
                "Show me all the consignment numbers",
                "What is the total transportation cost?",
                "What is the total consignment MRP value?",
                "What is the purpose of this logistics plan and what are the key identifiers?",
                "What are the origin and destination of the shipment?",
                "What mode of transport was used and what were the total load metrics?",
                "What is the total transportation cost associated with this consignment?",
                "When is the shipment scheduled to be dispatched and when is it expected to arrive?",
                "What product is being shipped in this consignment?"
            ]
        
        for example in normal_examples:
            btn_frame = tk.Frame(scroll_frame, bg=self.colors['bg_card'])
            btn_frame.pack(fill=tk.X, pady=2)
            
            example_btn = tk.Button(
                btn_frame,
                text=f"💡 {example}",
                command=lambda e=example: self.insert_example_from_info(e),
                bg=self.colors['hover'],
                fg=self.colors['text_primary'],
                font=('Segoe UI', 9),
                anchor=tk.W,
                padx=15,
                pady=8,
                cursor='hand2',
                relief=tk.FLAT,
                bd=0,
                activebackground=self.colors['success'],
                activeforeground='white'
            )
            example_btn.pack(fill=tk.X)
        
        # Intermediate Level Questions
        intermediate_label = tk.Label(
            scroll_frame,
            text="🟡 Intermediate Level Questions",
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['warning'],
            anchor=tk.W
        )
        intermediate_label.pack(anchor=tk.W, pady=(15, 8), padx=5)
        
        intermediate_examples = [
                "What is the total weight across all consignments?",
                "What is the average weight per consignment?",
                "What is the total volume across all consignments?",
                "What is the average volume per consignment?",
                "Which consignment has the highest transportation cost?",
                "Which consignment has the highest MRP value?",
                "What is the average mode utilization percentage?",
                "What is the average weight fill percentage?",
                "What is the average volume fill percentage?",
                "Show me all consignments going to a specific destination",
                "Show me all consignments coming from a specific source",
                "What is the total number of cases across all consignments?",
                "Which transportation mode is used most frequently?",
                "What is the total consignment MRP value for a specific customer?",
                "Show me consignments with weight fill percentage above 90%",
                "Show me consignments with volume fill percentage above 90%",
                "What is the average number of cases per consignment?",
                "Which consignment has the highest number of cases?",
                "What is the total cost for consignments using Truck-32Ft mode?",
                "Show me all consignments dispatched on a specific date",
                "What are the total cases for order with Product Code RO_27_786_25/10 and its contribution to consignment volume utilization?",
                "What are the number of cases and cost contribution for order with Product Code 209_29/10?",
                "What is the total number of cases for five distinct orders starting from RO_2_786_1/10 through 204_24/10?",
                "What are the utilization percentages for weight and volume fill?",
                "What is the mode utilization percentage for a specific order?",
                "What is the volume percentage fill for a specific product order?",
                "What is the consignment MRP value for a specific line item?",
                "Show me all orders for a specific product code",
                "What is the total weight and volume utilization for consignment 769?"
            ]
        
        for example in intermediate_examples:
            btn_frame = tk.Frame(scroll_frame, bg=self.colors['bg_card'])
            btn_frame.pack(fill=tk.X, pady=2)
            
            example_btn = tk.Button(
                btn_frame,
                text=f"💡 {example}",
                command=lambda e=example: self.insert_example_from_info(e),
                bg=self.colors['hover'],
                fg=self.colors['text_primary'],
                font=('Segoe UI', 9),
                anchor=tk.W,
                padx=15,
                pady=8,
                cursor='hand2',
                relief=tk.FLAT,
                bd=0,
                activebackground=self.colors['warning'],
                activeforeground='white'
            )
            example_btn.pack(fill=tk.X)
        
        # Hard Level Questions
        hard_label = tk.Label(
            scroll_frame,
            text="🔴 Hard Level Questions",
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['danger'],
            anchor=tk.W
        )
        hard_label.pack(anchor=tk.W, pady=(15, 8), padx=5)
        
        hard_examples = [
                "What is the cost per unit weight for each consignment?",
                "What is the cost per unit volume for each consignment?",
                "What is the cost efficiency ratio (cost per MRP value) for each consignment?",
                "Which consignments have the best utilization rates (weight and volume combined)?",
                "What is the average transit time in days for all consignments?",
                "Show me consignments with mode utilization below 50%",
                "What is the total transportation cost per destination?",
                "What is the total transportation cost per source location?",
                "Which customer has the highest total consignment value?",
                "What is the average consignment value per customer?",
                "Show me consignments where weight fill and volume fill are both above 95%",
                "What is the total number of cases per product across all consignments?",
                "Which product has the highest total number of cases?",
                "What is the total weight per product?",
                "What is the total volume per product?",
                "Show me consignments with the highest cost-to-value ratio",
                "What is the distribution of consignments by load type?",
                "What is the total MRP value per destination?",
                "What is the total MRP value per source?",
                "Which consignments have the lowest utilization rates?",
                "What is the average cases per product?",
                "Show me all details for consignment number 769",
                "What is the total cost for FTL load type consignments?",
                "What is the efficiency score (utilization vs cost) for each consignment?",
                "Calculate the total cases for orders RO_2_786_1/10, 203_23/10, 189_9/10, 204_24/10, and 199_19/10",
                "What is the contribution of each order to the overall consignment volume utilization?",
                "What is the weight percentage fill for each order in consignment 769?",
                "What is the volume percentage fill for each order in consignment 769?",
                "What is the mode utilization percentage for each order line item?",
                "What is the consignment MRP value breakdown by order?",
                "Show me the utilization metrics comparison across all orders in a consignment",
                "What is the cost per case for each order in the consignment?",
                "What is the cost per unit weight for each order line item?",
                "What is the cost per unit volume for each order line item?",
                "Which orders have the highest and lowest utilization percentages?",
                "What is the total contribution of all orders to the consignment's weight and volume fill?"
            ]
        
        for example in hard_examples:
            btn_frame = tk.Frame(scroll_frame, bg=self.colors['bg_card'])
            btn_frame.pack(fill=tk.X, pady=2)
            
            example_btn = tk.Button(
                btn_frame,
                text=f"💡 {example}",
                command=lambda e=example: self.insert_example_from_info(e),
                bg=self.colors['hover'],
                fg=self.colors['text_primary'],
                font=('Segoe UI', 9),
                anchor=tk.W,
                padx=15,
                pady=8,
                cursor='hand2',
                relief=tk.FLAT,
                bd=0,
                activebackground=self.colors['danger'],
                activeforeground='white'
            )
            example_btn.pack(fill=tk.X)
        
        # Update canvas scroll region after all widgets are added
        scroll_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Make sure canvas can receive focus for scrolling
        canvas.focus_set()
        
        # ========== TAB 2: System Information ==========
        system_frame = tk.Frame(notebook, bg=self.colors['bg_card'])
        notebook.add(system_frame, text="🔧 System Information")
        
        info_text_frame = scrolledtext.ScrolledText(
            system_frame,
            wrap=tk.WORD,
            font=('Segoe UI', 10),
            bg='white',
            fg=self.colors['text_primary'],
            padx=20,
            pady=20,
            relief=tk.FLAT,
            bd=0
        )
        info_text_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        system_info = """
═══════════════════════════════════════════════════════════════
  Excel/CSV to RAG System - System Information
═══════════════════════════════════════════════════════════════

📊 TECHNOLOGY STACK:
───────────────────────────────────────────────────────────────
• Model Type: Small Language Model (SLM)
• Embedding Model: Sentence Transformers (all-MiniLM-L6-v2)
• Vector Database: ChromaDB
• ML Framework: PyTorch / Transformers

🤖 AI/ML CAPABILITIES:
───────────────────────────────────────────────────────────────
✅ Uses ML Algorithms: YES
   - Sentence Embeddings (Transformer-based)
   - Vector Similarity Search
   - Semantic Understanding
   - Numeric Value Extraction

✅ Model Type: SLM (Small Language Model)
   - NOT an LLM (Large Language Model)
   - Optimized for embeddings and retrieval
   - Faster and more efficient
   - Runs completely offline

🌐 OFFLINE CAPABILITY:
───────────────────────────────────────────────────────────────
✅ Fully Offline: YES
   - No internet connection required
   - No API keys needed
   - All processing happens locally
   - Models bundled with application
   - 100% privacy - data never leaves your computer

📁 FILE COMPATIBILITY:
───────────────────────────────────────────────────────────────
✅ Multiple Excel Files: YES
   - Process multiple files
   - All files stored in same database
   - Query across all files simultaneously
   - Each file maintains its identity

✅ Multiple Excel Sheets: YES
   - Process all sheets with checkbox
   - Each sheet processed separately
   - Query across all sheets
   - Sheet-specific metadata

✅ Supported Formats:
   - Excel: .xlsx, .xls, .xlsm, .xlsb
   - CSV: .csv (auto-detects encoding)

🎯 FEATURES:
───────────────────────────────────────────────────────────────
• Natural Language Queries
• 100% Numeric Accuracy
• Semantic Search
• Multi-file Support
• Multi-sheet Support
• Download Answers
• Settings Configuration
• Example Questions

💡 HOW IT WORKS:
───────────────────────────────────────────────────────────────
1. Upload Excel/CSV file
2. System converts to structured Markdown
3. Content is chunked intelligently
4. ML model creates embeddings (vector representations)
5. Embeddings stored in vector database
6. Queries use semantic search to find relevant data
7. Results returned with 100% numeric accuracy

🔒 PRIVACY & SECURITY:
───────────────────────────────────────────────────────────────
• All data processed locally
• No cloud services
• No data transmission
• No external API calls
• Complete privacy guaranteed
        """
        
        info_text_frame.insert(1.0, system_info)
        info_text_frame.config(state=tk.DISABLED)
        
        # ========== TAB 3: Settings ==========
        settings_frame = tk.Frame(notebook, bg=self.colors['bg_card'])
        notebook.add(settings_frame, text="⚙️ Settings")
        
        settings_content = tk.Frame(settings_frame, bg=self.colors['bg_card'], padx=20, pady=20)
        settings_content.pack(fill=tk.BOTH, expand=True)
        
        # Files Folder Path Section (NEW)
        files_folder_header = tk.Label(
            settings_content,
            text="📂 Excel Files Folder Path",
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary'],
            anchor=tk.W
        )
        files_folder_header.pack(anchor=tk.W, pady=(0, 5))
        
        files_folder_help = tk.Label(
            settings_content,
            text="Select folder containing Excel/CSV files to load",
            font=('Segoe UI', 10),
            bg=self.colors['bg_card'],
            fg=self.colors['text_secondary'],
            anchor=tk.W
        )
        files_folder_help.pack(anchor=tk.W, pady=(0, 10))
        
        files_folder_frame = tk.Frame(settings_content, bg=self.colors['bg_card'])
        files_folder_frame.pack(fill=tk.X, pady=(0, 25))
        
        # Update files_folder_var with current path
        self.files_folder_var.set(self.files_folder_path)
        files_folder_entry = tk.Entry(
            files_folder_frame,
            textvariable=self.files_folder_var,
            font=('Segoe UI', 11),
            bg='white',
            fg=self.colors['text_primary'],
            relief=tk.SOLID,
            bd=1,
            highlightthickness=2,
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['primary'],
            insertbackground=self.colors['text_primary']
        )
        files_folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=0)
        
        def update_files_folder_from_entry():
            """Update files folder path when entry changes."""
            new_path = files_folder_entry.get()
            if new_path and os.path.exists(new_path):
                self.files_folder_path = new_path
                self.files_folder_var.set(new_path)
                self.save_settings()
                self.refresh_file_list()
        
        files_folder_entry.bind('<KeyRelease>', lambda e: update_files_folder_from_entry())
        files_folder_entry.bind('<FocusOut>', lambda e: update_files_folder_from_entry())
        
        def browse_files_folder():
            """Browse for files folder and update."""
            path = filedialog.askdirectory(
                initialdir=self.files_folder_path if os.path.exists(self.files_folder_path) else os.path.expanduser("~"),
                title="Select Folder Containing Excel/CSV Files"
            )
            if path:
                self.files_folder_path = path
                self.files_folder_var.set(path)
                files_folder_entry.delete(0, tk.END)
                files_folder_entry.insert(0, path)
                self.save_settings()
                self.refresh_file_list()
                messagebox.showinfo("Folder Updated", f"Files folder set to:\n{path}\n\nFile list will refresh automatically.")
        
        browse_files_folder_btn = tk.Button(
            files_folder_frame,
            text="📂 Browse",
            command=browse_files_folder,
            bg=self.colors['primary'],
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            padx=25,
            pady=12,
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            activebackground=self.colors['primary_dark'],
            activeforeground='white'
        )
        browse_files_folder_btn.pack(side=tk.LEFT)
        
        # Download Path Section
        download_header = tk.Label(
            settings_content,
            text="📁 Download Path",
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary'],
            anchor=tk.W
        )
        download_header.pack(anchor=tk.W, pady=(0, 5))
        
        help_label = tk.Label(
            settings_content,
            text="Select where to save downloaded answers",
            font=('Segoe UI', 10),
            bg=self.colors['bg_card'],
            fg=self.colors['text_secondary'],
            anchor=tk.W
        )
        help_label.pack(anchor=tk.W, pady=(0, 15))
        
        path_frame = tk.Frame(settings_content, bg=self.colors['bg_card'])
        path_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Update path_var with current download path
        self.path_var.set(self.download_path)
        path_entry = tk.Entry(
            path_frame,
            textvariable=self.path_var,
            font=('Segoe UI', 11),
            bg='white',
            fg=self.colors['text_primary'],
            relief=tk.SOLID,
            bd=1,
            highlightthickness=2,
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['primary'],
            insertbackground=self.colors['text_primary']
        )
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=0)
        
        def update_path_from_entry():
            """Update download path when entry changes."""
            new_path = path_entry.get()
            if new_path and os.path.exists(new_path):
                self.download_path = new_path
                self.path_var.set(new_path)
                self.save_settings()
        
        path_entry.bind('<KeyRelease>', lambda e: update_path_from_entry())
        path_entry.bind('<FocusOut>', lambda e: update_path_from_entry())
        
        def browse_and_update():
            """Browse for path and update both variables."""
            self.browse_download_path()
            # Update the entry field after browsing
            self.path_var.set(self.download_path)
            path_entry.delete(0, tk.END)
            path_entry.insert(0, self.download_path)
        
        browse_btn = tk.Button(
            path_frame,
            text="📂 Browse",
            command=browse_and_update,
            bg=self.colors['primary'],
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            padx=25,
            pady=12,
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            activebackground=self.colors['primary_dark'],
            activeforeground='white'
        )
        browse_btn.pack(side=tk.LEFT)
        
        # Quick Info Section
        quick_info_frame = tk.LabelFrame(
            settings_content,
            text="Quick Information",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary'],
            padx=15,
            pady=15
        )
        quick_info_frame.pack(fill=tk.X, pady=(20, 0))
        
        quick_info_text = """Technology: Small Language Model (SLM)
Model: Sentence Transformers (all-MiniLM-L6-v2)
Offline: ✅ Fully Offline (No Internet Required)
ML Algorithms: ✅ Yes (Embeddings, Vector Search)
Multiple Files: ✅ Supported
Multiple Sheets: ✅ Supported"""
        
        tk.Label(
            quick_info_frame,
            text=quick_info_text,
            font=('Segoe UI', 9),
            bg=self.colors['bg_card'],
            fg=self.colors['text_secondary'],
            justify=tk.LEFT,
            anchor=tk.W
        ).pack(anchor=tk.W, padx=5)
    
    def insert_example_from_info(self, example):
        """Insert example from info window and close it."""
        self.query_entry.delete(0, tk.END)
        self.query_entry.insert(0, example)
        self.query_entry.config(fg=self.colors['text_primary'])
        self.query_entry.focus()
        # Close the info window
        if hasattr(self, 'info_window') and self.info_window:
            try:
                self.info_window.destroy()
                self.info_window = None
            except Exception as e:
                print(f"Error closing info window: {e}")
                pass


def main():
    root = tk.Tk()
    app = ExcelRAGDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

