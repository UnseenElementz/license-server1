# -*- coding: utf-8 -*-
"""
Unseen Elementz License Manager v1.0
Standalone license management system for estate agents
Software created by Unseen elementz - For support message +447368417555
"""

import csv
import os
import json
import uuid
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

# --- FILE PATHS --- #
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSES_FILE = os.path.join(SCRIPT_DIR, "licenses.csv")

# Remote license server (you can change this to your server)
LICENSE_SERVER_URL = "https://your-server.com/api/license"  # TODO: Replace with your server URL
LICENSE_SERVER_TIMEOUT = 10  # seconds

# --- LICENSE MANAGEMENT --- #
def init_licenses_file():
    """Create licenses CSV file if it doesn't exist"""
    if not os.path.exists(LICENSES_FILE):
        with open(LICENSES_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "license_id", "agency_name", "contact_email", "contact_phone", 
                "license_key", "active", "seats", "created_at", "expires_at", 
                "notes", "last_used", "machine_ids"
            ])

def load_licenses():
    """Load all licenses from CSV"""
    licenses = []
    if not os.path.exists(LICENSES_FILE):
        return licenses
    
    with open(LICENSES_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert string booleans and numbers
            row['active'] = row.get('active', 'False').lower() == 'true'
            row['seats'] = int(row.get('seats', 1))
            licenses.append(row)
    return licenses

def save_licenses(licenses):
    """Save all licenses to CSV"""
    with open(LICENSES_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "license_id", "agency_name", "contact_email", "contact_phone", 
            "license_key", "active", "seats", "created_at", "expires_at", 
            "notes", "last_used", "machine_ids"
        ])
        for license in licenses:
            writer.writerow([
                license.get('license_id', ''),
                license.get('agency_name', ''),
                license.get('contact_email', ''),
                license.get('contact_phone', ''),
                license.get('license_key', ''),
                str(license.get('active', False)),
                license.get('seats', 1),
                license.get('created_at', ''),
                license.get('expires_at', ''),
                license.get('notes', ''),
                license.get('last_used', ''),
                license.get('machine_ids', '')
            ])

def generate_license_key():
    """Generate a unique license key"""
    return f"TZ-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"

def add_license(agency_name, contact_email, contact_phone, seats, expires_months, notes):
    """Add a new license"""
    licenses = load_licenses()
    
    # Check if agency already exists
    for license in licenses:
        if license['agency_name'].lower() == agency_name.lower():
            return False, "Agency already exists"
    
    new_license = {
        'license_id': str(uuid.uuid4()),
        'agency_name': agency_name,
        'contact_email': contact_email,
        'contact_phone': contact_phone,
        'license_key': generate_license_key(),
        'active': True,
        'seats': int(seats),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expires_at': (datetime.now() + timedelta(days=30*int(expires_months))).strftime('%Y-%m-%d'),
        'notes': notes,
        'last_used': '',
        'machine_ids': ''
    }
    
    licenses.append(new_license)
    save_licenses(licenses)
    return True, "License created successfully"

def toggle_license_status(license_id):
    """Toggle license active/inactive status"""
    licenses = load_licenses()
    for license in licenses:
        if license['license_id'] == license_id:
            license['active'] = not license['active']
            save_licenses(licenses)
            return True
    return False

def delete_license(license_id):
    """Delete a license"""
    licenses = load_licenses()
    licenses = [l for l in licenses if l['license_id'] != license_id]
    save_licenses(licenses)
    return True

def export_license_json(license_id):
    """Export a license as JSON for client delivery"""
    licenses = load_licenses()
    license = next((l for l in licenses if l['license_id'] == license_id), None)
    if not license:
        return None
    
    # Create export data (exclude sensitive internal fields)
    export_data = {
        'agency_name': license['agency_name'],
        'license_key': license['license_key'],
        'seats': license['seats'],
        'expires_at': license['expires_at'],
        'active': license['active']
    }
    
    return json.dumps(export_data, indent=2)

def sync_license_to_server(license_data):
    """Sync license status to remote server"""
    try:
        data = {
            'action': 'update_license',
            'license_key': license_data['license_key'],
            'agency_name': license_data['agency_name'],
            'active': license_data['active'],
            'expires_at': license_data['expires_at'],
            'seats': license_data['seats']
        }
        
        req_data = json.dumps(data).encode('utf-8')
        request = urllib.request.Request(
            LICENSE_SERVER_URL,
            data=req_data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(request, timeout=LICENSE_SERVER_TIMEOUT) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('success', False), result.get('message', '')
            
    except Exception as e:
        return False, f"Server sync failed: {str(e)}"

def disable_license_remotely(license_id):
    """Disable a license on the remote server"""
    licenses = load_licenses()
    license = next((l for l in licenses if l['license_id'] == license_id), None)
    if not license:
        return False, "License not found"
    
    # Update local license
    license['active'] = False
    save_licenses(licenses)
    
    # Try to sync to server
    success, message = sync_license_to_server(license)
    if success:
        return True, "License disabled locally and on server"
    else:
        return True, f"License disabled locally. Server sync failed: {message}"

# --- GUI FUNCTIONS --- #
def refresh_license_list():
    """Refresh the license list display"""
    # Clear existing items
    for item in tree.get_children():
        tree.delete(item)
    
    licenses = load_licenses()
    
    # Apply search filter
    search_term = search_var.get().lower()
    if search_term:
        licenses = [l for l in licenses if 
                   search_term in l['agency_name'].lower() or 
                   search_term in l['contact_email'].lower() or
                   search_term in l['license_key'].lower()]
    
    # Populate tree
    for license in licenses:
        status = "✅ Active" if license['active'] else "❌ Inactive"
        tree.insert("", "end", values=(
            license['agency_name'],
            license['contact_email'],
            license['license_key'],
            license['seats'],
            status,
            license['expires_at']
        ), tags=(license['license_id'],))

def add_license_window():
    """Open add license window"""
    win = tk.Toplevel(root)
    win.title("Add New License")
    win.geometry("500x400")
    win.configure(bg="black")
    win.grab_set()  # Modal window
    
    tk.Label(win, text="Add New License", font=("Arial", 16, "bold"), fg="orange", bg="black").pack(pady=10)
    
    # Form fields
    tk.Label(win, text="Agency Name:", fg="orange", bg="black").pack()
    entry_agency = tk.Entry(win, width=40)
    entry_agency.pack(pady=2)
    
    tk.Label(win, text="Contact Email:", fg="orange", bg="black").pack()
    entry_email = tk.Entry(win, width=40)
    entry_email.pack(pady=2)
    
    tk.Label(win, text="Contact Phone:", fg="orange", bg="black").pack()
    entry_phone = tk.Entry(win, width=40)
    entry_phone.pack(pady=2)
    
    tk.Label(win, text="Number of Seats:", fg="orange", bg="black").pack()
    entry_seats = tk.Entry(win, width=40)
    entry_seats.insert(0, "1")
    entry_seats.pack(pady=2)
    
    tk.Label(win, text="Expires in (months):", fg="orange", bg="black").pack()
    entry_expires = tk.Entry(win, width=40)
    entry_expires.insert(0, "12")
    entry_expires.pack(pady=2)
    
    tk.Label(win, text="Notes:", fg="orange", bg="black").pack()
    text_notes = tk.Text(win, width=40, height=4)
    text_notes.pack(pady=2)
    
    def save_license():
        agency = entry_agency.get().strip()
        email = entry_email.get().strip()
        phone = entry_phone.get().strip()
        seats = entry_seats.get().strip()
        expires = entry_expires.get().strip()
        notes = text_notes.get("1.0", tk.END).strip()
        
        if not agency or not email:
            messagebox.showerror("Error", "Agency name and email are required")
            return
        
        try:
            seats = int(seats) if seats else 1
            expires = int(expires) if expires else 12
        except ValueError:
            messagebox.showerror("Error", "Seats and expires must be numbers")
            return
        
        success, message = add_license(agency, email, phone, seats, expires, notes)
        if success:
            messagebox.showinfo("Success", message)
            win.destroy()
            refresh_license_list()
        else:
            messagebox.showerror("Error", message)
    
    tk.Button(win, text="Save License", bg="orange", fg="black", command=save_license).pack(pady=10)
    tk.Button(win, text="Cancel", bg="gray", fg="white", command=win.destroy).pack()

def edit_license_window():
    """Open edit license window"""
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a license to edit")
        return
    
    item = selected[0]
    license_id = tree.item(item, "tags")[0]
    
    licenses = load_licenses()
    license = next((l for l in licenses if l['license_id'] == license_id), None)
    if not license:
        messagebox.showerror("Error", "License not found")
        return
    
    win = tk.Toplevel(root)
    win.title("Edit License")
    win.geometry("500x400")
    win.configure(bg="black")
    win.grab_set()
    
    tk.Label(win, text="Edit License", font=("Arial", 16, "bold"), fg="orange", bg="black").pack(pady=10)
    
    # Form fields with current values
    tk.Label(win, text="Agency Name:", fg="orange", bg="black").pack()
    entry_agency = tk.Entry(win, width=40)
    entry_agency.insert(0, license['agency_name'])
    entry_agency.pack(pady=2)
    
    tk.Label(win, text="Contact Email:", fg="orange", bg="black").pack()
    entry_email = tk.Entry(win, width=40)
    entry_email.insert(0, license['contact_email'])
    entry_email.pack(pady=2)
    
    tk.Label(win, text="Contact Phone:", fg="orange", bg="black").pack()
    entry_phone = tk.Entry(win, width=40)
    entry_phone.insert(0, license['contact_phone'])
    entry_phone.pack(pady=2)
    
    tk.Label(win, text="Number of Seats:", fg="orange", bg="black").pack()
    entry_seats = tk.Entry(win, width=40)
    entry_seats.insert(0, str(license['seats']))
    entry_seats.pack(pady=2)
    
    tk.Label(win, text="Expires At (YYYY-MM-DD):", fg="orange", bg="black").pack()
    entry_expires = tk.Entry(win, width=40)
    entry_expires.insert(0, license['expires_at'])
    entry_expires.pack(pady=2)
    
    tk.Label(win, text="Notes:", fg="orange", bg="black").pack()
    text_notes = tk.Text(win, width=40, height=4)
    text_notes.insert("1.0", license['notes'])
    text_notes.pack(pady=2)
    
    def save_changes():
        license['agency_name'] = entry_agency.get().strip()
        license['contact_email'] = entry_email.get().strip()
        license['contact_phone'] = entry_phone.get().strip()
        license['seats'] = int(entry_seats.get().strip()) if entry_seats.get().strip() else 1
        license['expires_at'] = entry_expires.get().strip()
        license['notes'] = text_notes.get("1.0", tk.END).strip()
        
        if not license['agency_name'] or not license['contact_email']:
            messagebox.showerror("Error", "Agency name and email are required")
            return
        
        save_licenses(licenses)
        messagebox.showinfo("Success", "License updated successfully")
        win.destroy()
        refresh_license_list()
    
    tk.Button(win, text="Save Changes", bg="orange", fg="black", command=save_changes).pack(pady=10)
    tk.Button(win, text="Cancel", bg="gray", fg="white", command=win.destroy).pack()

def toggle_license():
    """Toggle selected license active/inactive status"""
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a license to toggle")
        return
    
    item = selected[0]
    license_id = tree.item(item, "tags")[0]
    
    if toggle_license_status(license_id):
        messagebox.showinfo("Success", "License status updated")
        refresh_license_list()
    else:
        messagebox.showerror("Error", "Failed to update license status")

def delete_license_confirm():
    """Delete selected license with confirmation"""
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a license to delete")
        return
    
    item = selected[0]
    agency_name = tree.item(item, "values")[0]
    license_id = tree.item(item, "tags")[0]
    
    if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the license for {agency_name}?\n\nThis action cannot be undone."):
        if delete_license(license_id):
            messagebox.showinfo("Success", "License deleted successfully")
            refresh_license_list()
        else:
            messagebox.showerror("Error", "Failed to delete license")

def export_license():
    """Export selected license as JSON file"""
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a license to export")
        return
    
    item = selected[0]
    agency_name = tree.item(item, "values")[0]
    license_id = tree.item(item, "tags")[0]
    
    json_data = export_license_json(license_id)
    if not json_data:
        messagebox.showerror("Error", "License not found")
        return
    
    try:
        # Ask user where to save the file
        filename = filedialog.asksaveasfilename(
            title="Export License",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{agency_name.replace(' ', '_')}_license.json"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(json_data)
                messagebox.showinfo("Success", f"License exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export license: {str(e)}")
    except Exception as e:
        messagebox.showerror("Error", f"File dialog error: {str(e)}")

def show_license_details():
    """Show detailed information about selected license"""
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a license to view details")
        return
    
    item = selected[0]
    license_id = tree.item(item, "tags")[0]
    
    licenses = load_licenses()
    license = next((l for l in licenses if l['license_id'] == license_id), None)
    if not license:
        messagebox.showerror("Error", "License not found")
        return
    
    win = tk.Toplevel(root)
    win.title("License Details")
    win.geometry("500x400")
    win.configure(bg="black")
    
    tk.Label(win, text="License Details", font=("Arial", 16, "bold"), fg="orange", bg="black").pack(pady=10)
    
    details_text = f"""
Agency Name: {license['agency_name']}
Contact Email: {license['contact_email']}
Contact Phone: {license['contact_phone']}
License Key: {license['license_key']}
Status: {'Active' if license['active'] else 'Inactive'}
Seats: {license['seats']}
Created: {license['created_at']}
Expires: {license['expires_at']}
Last Used: {license['last_used'] or 'Never'}
Machine IDs: {license['machine_ids'] or 'None'}
Notes: {license['notes']}
    """
    
    text_widget = tk.Text(win, bg="black", fg="white", font=("Arial", 10), wrap=tk.WORD)
    text_widget.insert("1.0", details_text)
    text_widget.config(state=tk.DISABLED)
    text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    tk.Button(win, text="Close", bg="gray", fg="white", command=win.destroy).pack(pady=10)

# --- MAIN GUI --- #
def main():
    global root, tree, search_var
    
    root = tk.Tk()
    root.title("Unseen Elementz License Manager v1.0")
    root.geometry("1000x600")
    root.configure(bg="black")
    
    # Header
    header_frame = tk.Frame(root, bg="#FF6B35", height=60)
    header_frame.pack(fill=tk.X)
    header_frame.pack_propagate(False)
    
    tk.Label(header_frame, text="🔐 Unseen Elementz License Manager v1.0", 
             font=("Arial", 18, "bold"), fg="black", bg="#FF6B35").pack(expand=True)
    
    # Search and controls
    controls_frame = tk.Frame(root, bg="black")
    controls_frame.pack(fill=tk.X, padx=10, pady=10)
    
    tk.Label(controls_frame, text="Search:", fg="orange", bg="black").pack(side=tk.LEFT)
    search_var = tk.StringVar()
    search_entry = tk.Entry(controls_frame, textvariable=search_var, width=30)
    search_entry.pack(side=tk.LEFT, padx=5)
    search_entry.bind('<KeyRelease>', lambda e: refresh_license_list())
    
    def create_test_license():
        """Create a test license for testing purposes"""
        success, message = add_license("Test Agency", "test@example.com", "01234567890", 1, 12, "Test license for development")
        if success:
            messagebox.showinfo("Success", "Test license created successfully!")
            refresh_license_list()
        else:
            messagebox.showerror("Error", message)
    
    def disable_remotely():
        """Disable selected license remotely"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a license to disable")
            return
        
        item = selected[0]
        agency_name = tree.item(item, "values")[0]
        license_id = tree.item(item, "tags")[0]
        
        if messagebox.askyesno("Confirm Remote Disable", 
                              f"Are you sure you want to DISABLE this license remotely?\n\n"
                              f"Agency: {agency_name}\n\n"
                              f"This will immediately stop the client from using the software!"):
            success, message = disable_license_remotely(license_id)
            if success:
                messagebox.showinfo("Success", message)
                refresh_license_list()
            else:
                messagebox.showerror("Error", message)
    
    tk.Button(controls_frame, text="Add License", bg="green", fg="white", 
              command=add_license_window).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, text="Test License", bg="yellow", fg="black", 
              command=create_test_license).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, text="Edit", bg="blue", fg="white", 
              command=edit_license_window).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, text="Toggle Status", bg="orange", fg="black", 
              command=toggle_license).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, text="Export JSON", bg="purple", fg="white", 
              command=export_license).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, text="Disable Remotely", bg="red", fg="white", 
              command=disable_remotely).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, text="Details", bg="cyan", fg="black", 
              command=show_license_details).pack(side=tk.LEFT, padx=5)
    tk.Button(controls_frame, text="Delete", bg="gray", fg="white", 
              command=delete_license_confirm).pack(side=tk.LEFT, padx=5)
    
    # License list
    list_frame = tk.Frame(root)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Treeview with scrollbar
    scrollbar = ttk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    tree = ttk.Treeview(list_frame, columns=("Agency", "Email", "License Key", "Seats", "Status", "Expires"), 
                       show="headings", yscrollcommand=scrollbar.set)
    
    # Configure columns
    tree.heading("Agency", text="Agency Name")
    tree.heading("Email", text="Contact Email")
    tree.heading("License Key", text="License Key")
    tree.heading("Seats", text="Seats")
    tree.heading("Status", text="Status")
    tree.heading("Expires", text="Expires")
    
    tree.column("Agency", width=150)
    tree.column("Email", width=200)
    tree.column("License Key", width=200)
    tree.column("Seats", width=60)
    tree.column("Status", width=80)
    tree.column("Expires", width=100)
    
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=tree.yview)
    
    # Style the treeview
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Treeview", background="black", foreground="orange", fieldbackground="black", font=("Arial", 9))
    style.configure("Treeview.Heading", background="orange", foreground="black", font=("Arial", 9, "bold"))
    style.map("Treeview", background=[("selected", "orange")], foreground=[("selected", "black")])
    
    # Footer
    footer_frame = tk.Frame(root, bg="#1A1A1A", height=40)
    footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
    footer_frame.pack_propagate(False)
    
    tk.Label(footer_frame, text="© 2025 Unseen Elementz - License Management System v1.0", 
             font=("Arial", 8), fg="gray", bg="#1A1A1A").pack(expand=True)
    
    # Initialize and load data
    init_licenses_file()
    refresh_license_list()
    
    root.mainloop()

if __name__ == "__main__":
    main()
