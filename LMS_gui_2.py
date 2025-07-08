import sqlite3
import tkinter as tk
from tkinter import messagebox


#database connection
def get_database_connection():
    return sqlite3.connect("LMS_1.db")


#feature 1: Checkout Book 
def checkout_book():
    book_id = entry_book_id.get().strip()      # Get book ID from user input
    branch_id = entry_branch_id.get().strip()  # Get branch ID from user input
    card_no = entry_card_no.get().strip()      # Get card number from user input
    due_date = entry_due_date.get().strip()   # Get due date from user input

    #validate inputs
    if not book_id or not branch_id or not card_no or not due_date:
        messagebox.showerror("Error", "All field must be filled out.")
        return

    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        #insert a new record into BOOK_LOANS
        cursor.execute("""
            INSERT INTO BOOK_LOANS (Book_Id, Branch_Id, Card_No, Date_Out, Due_Date)
            VALUES (?, ?, ?, DATE('now'), ?);
        """, (book_id, branch_id, card_no, due_date))

        #fetch the updated Book_Copies for the specified book + branch
        cursor.execute("""
            SELECT * FROM BOOK_COPIES
            WHERE Book_Id = ? AND Branch_Id = ?;
        """, (book_id, branch_id))
        updated_copies = cursor.fetchall()

        # cmmit the transaction....
        conn.commit()

        #display updated Book_Copies
        if updated_copies:
            result = "\n".join([f"Book ID: {row[0]}, Branch ID: {row[1]}, Copies Left: {row[2]}" for row in updated_copies])
            messagebox.showinfo("Checkout Successful", f"Updated Book Copies:\n{result}")
        else:
            messagebox.showinfo("No Data", "No copies found for the specified book and branch.")
    except sqlite3.IntegrityError as e:
        messagebox.showerror("Error", f"Database integrity error: {e}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        conn.close()


#feature 2:add a borrower
def add_borrower():
    name = entry_borrower_name.get()
    address = entry_borrower_address.get()
    phone = entry_borrower_phone.get() 

    #validation checks:
    if not name.strip():
        messagebox.showerror("Error", "Name cannot be empty.")
        return
    if not address.strip():
        messagebox.showerror("Error", "Address cannot be empty.")
        return
    
    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO BORROWER (Name, Address, Phone)
            VALUES (?, ?, ?);
        """, (name, address, phone))
        
        cursor.execute("SELECT last_insert_rowid() AS CardNo;")
        new_card = cursor.fetchone()[0]

        conn.commit()
        messagebox.showinfo("Success", f"New Borrower Added! Card Number: {new_card}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        conn.close()


#feature 3: add a Book
def add_book():
    title = entry_new_book_title.get().strip()
    publisher_name = entry_publisher_name.get().strip()
    author_name = entry_author_name.get().strip()

    #validate the inputs
    if not title or not publisher_name or not author_name:
        messagebox.showerror("Error", "All fields must be filled out to add a book.")
        return

    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        #insert new book into BOOK table (auto generates 'Book_Id')
        cursor.execute("""
            INSERT INTO BOOK (Title, Publisher_Name)
            VALUES (?, ?);
        """, (title, publisher_name))
        
        #fetch the auto generated "Book_Id"
        book_id = cursor.lastrowid

        #insert the book's author into --> 'BOOK_AUTHORS' table
        cursor.execute("""
            INSERT INTO BOOK_AUTHORS (Book_Id, Author_Name)
            VALUES (?, ?);
        """, (book_id, author_name))

        #dynamically fetch all Branch ids
        cursor.execute("SELECT Branch_Id FROM LIBRARY_BRANCH;")
        branch_ids = [row[0] for row in cursor.fetchall()]

        #add 5 copies of the book to each branch
        for branch_id in branch_ids:
            cursor.execute("""
                INSERT INTO BOOK_COPIES (Book_Id, Branch_Id, No_Of_Copies)
                VALUES (?, ?, 5);
            """, (book_id, branch_id))

        conn.commit()
        messagebox.showinfo("Success", f"Book '{title}' added to all branches with ID {book_id}!")
    except sqlite3.IntegrityError as e:
        messagebox.showerror("Error", f"Integrity error: {e}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        conn.close()

#feature 4: list out the loaned copies
def list_loaned_copies():
    title = entry_loaned_title.get().strip()  #strip the spaces from the input

    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        #debugging print to verify input.....
        #print("Title:", title)

        #updated query for case-insensitive + partial title matching
        cursor.execute("""
            SELECT 
                BOOK_LOANS.Branch_Id, 
                COUNT(BOOK_LOANS.Book_Id) AS LoanedCopies
            FROM 
                BOOK_LOANS
            INNER JOIN 
                BOOK ON BOOK_LOANS.Book_Id = BOOK.Book_Id
            WHERE 
                UPPER(BOOK.Title) LIKE '%' || UPPER(?) || '%'
            GROUP BY 
                BOOK_LOANS.Branch_Id;
        """, (title,))
        
        #fetch results: 
        loaned_copies = cursor.fetchall()
        if loaned_copies:
            result = "\n".join([f"Branch {row[0]}: {row[1]} copies" for row in loaned_copies])
            messagebox.showinfo("Loaned Copies", f"Loaned Copies:\n{result}")
        else:
            messagebox.showinfo("No Data", "No loaned copies found for the given title.")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        conn.close()


#feature 5: list out the late loans
def list_late_loans():
    start_date = entry_start_date.get().strip()  #get start date from the GUI
    end_date = entry_end_date.get().strip()      # get end date from the GUI

    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        #execute the SQL query with the user provided date range
        cursor.execute("""
            SELECT 
                Book_Id,
                Branch_Id,
                Card_No,
                Due_Date,
                Returned_date,
                (JULIANDAY(Returned_date) - JULIANDAY(Due_Date)) AS DaysLate
            FROM 
                BOOK_LOANS
            WHERE 
                Returned_date > Due_Date 
                AND Due_Date BETWEEN ? AND ?;
        """, (start_date, end_date))
        
        #fetch results:
        late_loans = cursor.fetchall()
        if late_loans:
            result = "\n".join(
                [f"Book {row[0]} at Branch {row[1]}, Borrower {row[2]}: Due {row[3]}, Returned {row[4]}, Days Late: {row[5]}"
                 for row in late_loans]  #makes sure only process exactly 6 columns
            )
            messagebox.showinfo("Late Loans", f"Results:\n{result}")
        else:
            messagebox.showinfo("No Data", "No late loans found for the given date range.")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        conn.close()


#feature 6a: borrowers with late fees
def list_borrower_late_fees():
    borrower_id = entry_borrower_id.get().strip()             #cleans input
    borrower_name = entry_borrower_name_search.get().strip()  #  ^^^^^^^^

    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        #debugging: see the exact parameters passed
        #print("Borrower ID:", borrower_id)
        #print("Borrower Name:", borrower_name)

        #run query for case insensitive + partial name matching
        cursor.execute("""
            SELECT 
                Card_No AS Borrower_ID,
                Borrower_Name,
                CASE 
                    WHEN LateFeeBalance IS NULL OR LateFeeBalance = 0 THEN '$0.00'
                    ELSE '$' || printf('%.2f', LateFeeBalance)
                END AS Late_Fee_Balance
            FROM 
                vBookLoanInfo
            WHERE 
                (? IS NULL OR Card_No = ?)
                AND (? IS NULL OR UPPER(Borrower_Name) LIKE '%' || UPPER(?) || '%')
            ORDER BY 
                LateFeeBalance DESC;
        """, (
            borrower_id if borrower_id else None, 
            borrower_id if borrower_id else None, 
            borrower_name if borrower_name else None, 
            borrower_name if borrower_name else None
        ))
        
        #fetch results and display them:
        borrowers = cursor.fetchall()
        if borrowers:
            result = "\n".join([f"Borrower {row[0]} ({row[1]}): {row[2]}" for row in borrowers])
            messagebox.showinfo("Borrowers with Late Fees", f"Results:\n{result}")
        else:
            messagebox.showinfo("No Data", "No borrowers found.")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        conn.close()


#feature 6b: books w/ late fees
def list_books_with_late_fees():
    borrower_id = entry_borrower_id_for_books.get().strip()  #clean input
    book_title = entry_book_title_search.get().strip()       # ^^^^

    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        #run query for books w late fees
        cursor.execute("""
            SELECT 
                Book_Title AS Book_Title,
                CASE 
                    WHEN LateFeeBalance IS NULL THEN 'Non-Applicable'
                    ELSE '$' || printf('%.2f', LateFeeBalance)
                END AS Late_Fee
            FROM 
                vBookLoanInfo
            WHERE 
                (? IS NULL OR Card_No = ?)
                AND (? IS NULL OR UPPER(Book_Title) LIKE '%' || UPPER(?) || '%')
            ORDER BY 
                LateFeeBalance DESC;
        """, (
            borrower_id if borrower_id else None,
            borrower_id if borrower_id else None,
            book_title if book_title else None,
            book_title if book_title else None
        ))

        #fetch results:
        books = cursor.fetchall()
        if books:
            result = "\n".join([f"Book '{row[0]}': {row[1]}" for row in books])
            messagebox.showinfo("Books with Late Fees", f"Results:\n{result}")
        else:
            messagebox.showinfo("No Data", "No books found.")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        conn.close()


#clear fields functions
def clear_checkout_fields():
    entry_book_id.delete(0, tk.END)
    entry_branch_id.delete(0, tk.END)
    entry_card_no.delete(0, tk.END)
    entry_due_date.delete(0, tk.END)

def clear_borrower_fields():
    entry_borrower_name.delete(0, tk.END)
    entry_borrower_address.delete(0, tk.END)
    entry_borrower_phone.delete(0, tk.END)

def clear_book_fields():
    entry_new_book_title.delete(0, tk.END)
    entry_publisher_name.delete(0, tk.END)
    entry_author_name.delete(0, tk.END)

#GUI Implementation..................................................................
root = tk.Tk()
root.title("Library Management System")

#checkout book section
tk.Label(root, text="Checkout Book").grid(row=0, column=0, columnspan=2)
tk.Label(root, text="Book ID:").grid(row=1, column=0)
entry_book_id = tk.Entry(root)
entry_book_id.grid(row=1, column=1)
tk.Label(root, text="Branch ID:").grid(row=2, column=0)
entry_branch_id = tk.Entry(root)
entry_branch_id.grid(row=2, column=1)
tk.Label(root, text="Card No:").grid(row=3, column=0)
entry_card_no = tk.Entry(root)
entry_card_no.grid(row=3, column=1)
tk.Label(root, text="Due Date (YYYY-MM-DD):").grid(row=4, column=0)
entry_due_date = tk.Entry(root)
entry_due_date.grid(row=4, column=1)
tk.Button(root, text="Checkout", command=checkout_book).grid(row=5, column=0, columnspan=2)
tk.Button(root, text="Clear Fields", command=clear_checkout_fields).grid(row=6, column=0, columnspan=2)

#add borrower section
tk.Label(root, text="Add Borrower").grid(row=7, column=0, columnspan=2)
tk.Label(root, text="Name:").grid(row=8, column=0)
entry_borrower_name = tk.Entry(root)
entry_borrower_name.grid(row=8, column=1)
tk.Label(root, text="Address:").grid(row=9, column=0)
entry_borrower_address = tk.Entry(root)
entry_borrower_address.grid(row=9, column=1)
tk.Label(root, text="Phone Number:").grid(row=10, column=0) 
entry_borrower_phone = tk.Entry(root) 
entry_borrower_phone.grid(row=10, column=1)
tk.Button(root, text="Add Borrower", command=add_borrower).grid(row=11, column=0, columnspan=2)
tk.Button(root, text="Clear Fields", command=clear_borrower_fields).grid(row=12, column=0, columnspan=2)

#add Book section
tk.Label(root, text="Add Book").grid(row=13, column=0, columnspan=2)
tk.Label(root, text="Title:").grid(row=15, column=0)
entry_new_book_title = tk.Entry(root)
entry_new_book_title.grid(row=15, column=1)
tk.Label(root, text="Publisher Name:").grid(row=16, column=0)
entry_publisher_name = tk.Entry(root)
entry_publisher_name.grid(row=16, column=1)
tk.Label(root, text="Author Name:").grid(row=17, column=0)
entry_author_name = tk.Entry(root)
entry_author_name.grid(row=17, column=1)
tk.Button(root, text="Add Book", command=add_book).grid(row=18, column=0, columnspan=2)
tk.Button(root, text="Clear Fields", command=clear_book_fields).grid(row=19, column=0, columnspan=2)

#list the loaned copies Section
tk.Label(root, text="List Loaned Copies").grid(row=20, column=0, columnspan=2)
tk.Label(root, text="Book Title:").grid(row=21, column=0)
entry_loaned_title = tk.Entry(root)
entry_loaned_title.grid(row=21, column=1)
tk.Button(root, text="List Loaned Copies", command=list_loaned_copies).grid(row=22, column=0, columnspan=2)

#list late loans section
tk.Label(root, text="List Late Loans").grid(row=23, column=0, columnspan=2)
tk.Label(root, text="Start Date (YYYY-MM-DD):").grid(row=24, column=0)
entry_start_date = tk.Entry(root)
entry_start_date.grid(row=24, column=1)
tk.Label(root, text="End Date (YYYY-MM-DD):").grid(row=25, column=0)
entry_end_date = tk.Entry(root)
entry_end_date.grid(row=25, column=1)
tk.Button(root, text="List Late Loans", command=list_late_loans).grid(row=26, column=0, columnspan=2)

#borrowers w late fees section
tk.Label(root, text="Borrowers with Late Fees").grid(row=27, column=0, columnspan=2)
tk.Label(root, text="Borrower ID:").grid(row=28, column=0)
entry_borrower_id = tk.Entry(root)
entry_borrower_id.grid(row=28, column=1)
tk.Label(root, text="Borrower Name:").grid(row=29, column=0)
entry_borrower_name_search = tk.Entry(root)
entry_borrower_name_search.grid(row=29, column=1)
tk.Button(root, text="List Borrowers", command=list_borrower_late_fees).grid(row=30, column=0, columnspan=2)

#books w/ late fees section
tk.Label(root, text="Books with Late Fees").grid(row=31, column=0, columnspan=2)
tk.Label(root, text="Borrower ID:").grid(row=32, column=0)
entry_borrower_id_for_books = tk.Entry(root)
entry_borrower_id_for_books.grid(row=32, column=1)
tk.Label(root, text="Book Title:").grid(row=34, column=0)
entry_book_title_search = tk.Entry(root)
entry_book_title_search.grid(row=34, column=1)
tk.Button(root, text="List Books", command=list_books_with_late_fees).grid(row=35, column=0, columnspan=2)

#this is where magic starts: GUI loop........
root.mainloop()
