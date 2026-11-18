from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import get_db_connection, log_status_change
from app.services.auth_service import login_required
from app.services.notification_service import create_notification

claims_bp = Blueprint('claims', __name__)

@claims_bp.route('/claim/<int:found_id>', methods=['GET', 'POST'])
@login_required
def submit_claim(found_id):
    user_id = session['user_id']
    conn = get_db_connection()
    
    found_item = conn.execute('''
        SELECT f.*, u.name as finder_name 
        FROM found_items f 
        JOIN users u ON f.user_id = u.id 
        WHERE f.id = ?
    ''', (found_id,)).fetchone()
    
    if not found_item:
        conn.close()
        flash('Found item not found.', 'danger')
        return redirect(url_for('items.browse'))
        
    if found_item['user_id'] == user_id:
        conn.close()
        flash('You cannot claim an item that you reported finding.', 'warning')
        return redirect(url_for('items.view_found', item_id=found_id))
        
    # Check if user already claimed this
    existing = conn.execute('SELECT * FROM claims WHERE found_item_id = ? AND claimant_id = ?', (found_id, user_id)).fetchone()
    if existing:
        conn.close()
        flash('You have already submitted a claim for this item. Check status in My Claims.', 'info')
        return redirect(url_for('claims.my_claims'))
        
    # Find any of user's lost items that could be linked
    my_lost_items = conn.execute('''
        SELECT id, item_name, category FROM lost_items 
        WHERE user_id = ? AND status != 'Returned'
    ''', (user_id,)).fetchall()
    
    if request.method == 'POST':
        claimant_details = request.form.get('claimant_details', '').strip()
        contact_note = request.form.get('contact_note', '').strip()
        lost_item_id = request.form.get('lost_item_id', type=int)
        
        if not claimant_details:
            flash('Please provide distinguishing details or proof of ownership to verify your claim.', 'danger')
            conn.close()
            return render_template('claims/submit_claim.html', found_item=found_item, my_lost_items=my_lost_items)
            
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO claims (found_item_id, lost_item_id, claimant_id, claimant_details, contact_note, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        ''', (found_id, lost_item_id, user_id, claimant_details, contact_note))
        claim_id = cursor.lastrowid
        
        # Update found item status to 'Claim Requested'
        conn.execute("UPDATE found_items SET status = 'Claim Requested', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (found_id,))
        if lost_item_id:
            conn.execute("UPDATE lost_items SET status = 'Claim Requested', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (lost_item_id,))
            
        conn.commit()
        
        # Log status change in history
        log_status_change('found', found_id, found_item['status'], 'Claim Requested', f"Claim #{claim_id} submitted by {session['user_name']}", user_id, conn=conn)
        if lost_item_id:
            log_status_change('lost', lost_item_id, 'Matched', 'Claim Requested', f"Owner submitted claim #{claim_id} for matching found item #{found_id}", user_id, conn=conn)
            
        # Notify finder
        create_notification(
            found_item['user_id'],
            "New Ownership Claim Submitted",
            f"{session['user_name']} has submitted a claim with distinguishing proof for '{found_item['item_name']}'.",
            f"/claims/review/{claim_id}",
            conn=conn
        )
        
        conn.close()
        flash('Your claim has been submitted! The finder has been notified to review your distinguishing proof.', 'success')
        return redirect(url_for('claims.my_claims'))
        
    conn.close()
    return render_template('claims/submit_claim.html', found_item=found_item, my_lost_items=my_lost_items)

@claims_bp.route('/claims/my-claims')
@login_required
def my_claims():
    user_id = session['user_id']
    conn = get_db_connection()
    
    claims = conn.execute('''
        SELECT c.*, f.item_name as found_name, f.category as found_category, 
               f.found_location, f.storage_location, f.photo_filename as found_photo,
               u.name as finder_name, u.email as finder_email, u.phone as finder_phone
        FROM claims c
        JOIN found_items f ON c.found_item_id = f.id
        JOIN users u ON f.user_id = u.id
        WHERE c.claimant_id = ?
        ORDER BY c.created_at DESC
    ''', (user_id,)).fetchall()
    
    conn.close()
    return render_template('claims/my_claims.html', claims=claims)

@claims_bp.route('/claims/received')
@login_required
def received_claims():
    user_id = session['user_id']
    conn = get_db_connection()
    
    # Claims for items found by current user
    claims = conn.execute('''
        SELECT c.*, f.item_name as found_name, f.category as found_category, f.distinguishing_details as private_details,
               u.name as claimant_name, u.email as claimant_email, u.phone as claimant_phone
        FROM claims c
        JOIN found_items f ON c.found_item_id = f.id
        JOIN users u ON c.claimant_id = u.id
        WHERE f.user_id = ?
        ORDER BY c.created_at DESC
    ''', (user_id,)).fetchall()
    
    conn.close()
    return render_template('claims/received_claims.html', claims=claims)

@claims_bp.route('/claims/review/<int:claim_id>', methods=['GET', 'POST'])
@login_required
def review_claim(claim_id):
    user_id = session['user_id']
    user_role = session.get('user_role')
    conn = get_db_connection()
    
    claim = conn.execute('''
        SELECT c.*, 
               f.item_name as found_name, f.category as found_category, f.found_location,
               f.distinguishing_details as private_details, f.storage_location, f.status as found_status,
               f.user_id as finder_id,
               claimant.name as claimant_name, claimant.email as claimant_email, claimant.phone as claimant_phone,
               finder.name as finder_name, finder.email as finder_email, finder.phone as finder_phone
        FROM claims c
        JOIN found_items f ON c.found_item_id = f.id
        JOIN users claimant ON c.claimant_id = claimant.id
        JOIN users finder ON f.user_id = finder.id
        WHERE c.id = ?
    ''', (claim_id,)).fetchone()
    
    if not claim:
        conn.close()
        flash('Claim record not found.', 'danger')
        return redirect(url_for('items.dashboard'))
        
    # Only the finder or an administrator can review the claim
    if claim['finder_id'] != user_id and user_role != 'admin':
        conn.close()
        flash('Access unauthorized. Only the finder or admin may verify this claim.', 'danger')
        return redirect(url_for('items.dashboard'))
        
    if request.method == 'POST':
        action = request.form.get('action') # 'approve' or 'reject'
        review_notes = request.form.get('review_notes', '').strip()
        
        if action == 'approve':
            conn.execute('''
                UPDATE claims 
                SET status = 'Approved', review_notes = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (review_notes, user_id, claim_id))
            
            # Update Found Item status to 'Verified'
            log_status_change('found', claim['found_item_id'], claim['found_status'], 'Verified', f"Claim approved by {session['user_name']}. Ready for handover.", user_id, conn=conn)
            
            # If linked to lost item, update that too
            if claim['lost_item_id']:
                log_status_change('lost', claim['lost_item_id'], 'Claim Requested', 'Verified', f"Ownership verified against Found Item #{claim['found_item_id']}", user_id, conn=conn)
                
            create_notification(
                claim['claimant_id'],
                "Claim Approved! Ownership Verified",
                f"Your claim for '{claim['found_name']}' was approved! You can now coordinate handover with the finder.",
                f"/claims/my-claims",
                conn=conn
            )
            flash('Claim verified and approved! Mutual contact details are now unlocked for handover coordination.', 'success')
            
        elif action == 'reject':
            conn.execute('''
                UPDATE claims 
                SET status = 'Rejected', review_notes = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (review_notes, user_id, claim_id))
            
            # Revert found item back to Matched or Reported
            log_status_change('found', claim['found_item_id'], claim['found_status'], 'Reported', f"Claim #{claim_id} rejected: {review_notes}", user_id, conn=conn)
            if claim['lost_item_id']:
                log_status_change('lost', claim['lost_item_id'], 'Claim Requested', 'Reported', f"Claim rejected by finder", user_id, conn=conn)
                
            create_notification(
                claim['claimant_id'],
                "Claim Status Update",
                f"Your claim for '{claim['found_name']}' could not be verified with the provided details.",
                f"/claims/my-claims",
                conn=conn
            )
            flash('Claim has been marked as rejected.', 'info')
            
        conn.commit()
        conn.close()
        return redirect(url_for('claims.review_claim', claim_id=claim_id))
        
    conn.close()
    return render_template('claims/review_claim.html', claim=claim)

@claims_bp.route('/claims/handover-complete/<int:found_id>', methods=['POST'])
@login_required
def complete_handover(found_id):
    user_id = session['user_id']
    user_role = session.get('user_role')
    conn = get_db_connection()
    
    found_item = conn.execute('SELECT * FROM found_items WHERE id = ?', (found_id,)).fetchone()
    if not found_item:
        conn.close()
        flash('Item not found.', 'danger')
        return redirect(url_for('items.dashboard'))
        
    if found_item['user_id'] != user_id and user_role != 'admin':
        conn.close()
        flash('Only the finder or an administrator can confirm handover completion.', 'danger')
        return redirect(url_for('items.view_found', item_id=found_id))
        
    # Mark item returned!
    log_status_change('found', found_id, found_item['status'], 'Returned', f"Handover completed successfully. Item returned to verified owner.", user_id, conn=conn)
    
    # Mark linked approved claim's lost item returned as well
    approved_claim = conn.execute('''
        SELECT * FROM claims WHERE found_item_id = ? AND status = 'Approved'
    ''', (found_id,)).fetchone()
    
    if approved_claim and approved_claim['lost_item_id']:
        log_status_change('lost', approved_claim['lost_item_id'], 'Verified', 'Returned', f"Item returned via Found Item #{found_id}", user_id, conn=conn)
        create_notification(
            approved_claim['claimant_id'],
            "Item Successfully Recovered!",
            f"Your lost item '{found_item['item_name']}' is now marked as Returned! Thank you for using FindBack.",
            f"/lost/{approved_claim['lost_item_id']}",
            conn=conn
        )
        
    conn.commit()
    conn.close()
    
    flash('Item officially marked as RETURNED! Recovery logged in the system.', 'success')
    return redirect(url_for('items.view_found', item_id=found_id))
