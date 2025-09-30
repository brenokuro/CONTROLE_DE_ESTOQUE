let inventory = {};
let currentEditItem = null;
let isAdmin = false;

async function loadInventory() {
    try {
        const response = await fetch('/api/inventory');
        const data = await response.json();
        
        inventory = data.inventory;
        isAdmin = data.is_admin;
        renderInventory();

        // Se for admin, mostrar formulário de criação
        if (isAdmin) {
            document.getElementById('createItemSection').style.display = 'block';
        } else {
            document.getElementById('createItemSection').style.display = 'none';
        }

        if (isAdmin && data.low_stock_items && data.low_stock_items.length > 0) {
            showLowStockNotifications(data.low_stock_items);
        } else if (!isAdmin) {
            document.getElementById('notifications').innerHTML = '';
        }
    } catch (error) {
        console.error('Erro ao carregar estoque:', error);
    }
}

function renderInventory() {
    const grid = document.getElementById('inventoryGrid');
    grid.innerHTML = '';
    
    for (const [itemName, itemData] of Object.entries(inventory)) {
        const itemCard = createInventoryCard(itemName, itemData);
        grid.appendChild(itemCard);
    }
}

function createInventoryCard(itemName, itemData) {
    const card = document.createElement('div');
    card.className = 'inventory-item';
    
    if (itemData.quantity <= 5) {
        card.classList.add('low-stock');
    }
    
    card.innerHTML = `
        <div class="item-header">
            <div class="item-name">${itemName}</div>
            <div class="item-unit">${itemData.unit}</div>
        </div>
        <div class="item-quantity" data-item="${itemName}">
            ${itemData.quantity}
        </div>
        <div class="item-controls">
            <button class="btn-control btn-decrease" data-item="${itemName}">−</button>
            <button class="btn-control btn-increase" data-item="${itemName}">+</button>
        </div>
    `;
    
    const quantityDiv = card.querySelector('.item-quantity');
    quantityDiv.addEventListener('click', () => {
        openEditModal(itemName, itemData.quantity);
    });
    
    const decreaseBtn = card.querySelector('.btn-decrease');
    decreaseBtn.addEventListener('click', () => {
        updateQuantity(itemName, Math.max(0, itemData.quantity - 1));
    });
    
    const increaseBtn = card.querySelector('.btn-increase');
    increaseBtn.addEventListener('click', () => {
        updateQuantity(itemName, itemData.quantity + 1);
    });
    
    return card;
}

async function updateQuantity(itemName, newQuantity) {
    try {
        const response = await fetch('/api/update_inventory', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                item: itemName,
                quantity: newQuantity
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            inventory[itemName].quantity = newQuantity;
            renderInventory();
            
            if (isAdmin && newQuantity <= 5) {
                const lowStockItems = Object.entries(inventory)
                    .filter(([_, data]) => data.quantity <= 5)
                    .map(([name, _]) => name);
                showLowStockNotifications(lowStockItems);
            }
        }
    } catch (error) {
        console.error('Erro ao atualizar quantidade:', error);
    }
}

function openEditModal(itemName, currentQuantity) {
    currentEditItem = itemName;
    const modal = document.getElementById('editModal');
    const modalItemName = document.getElementById('modalItemName');
    const modalQuantity = document.getElementById('modalQuantity');
    
    modalItemName.textContent = itemName;
    modalQuantity.value = currentQuantity;
    
    modal.classList.add('show');
    modalQuantity.focus();
}

function closeEditModal() {
    const modal = document.getElementById('editModal');
    modal.classList.remove('show');
    currentEditItem = null;
}

function saveModalEdit() {
    const modalQuantity = document.getElementById('modalQuantity');
    const newQuantity = parseInt(modalQuantity.value);
    
    if (!isNaN(newQuantity) && newQuantity >= 0 && currentEditItem) {
        updateQuantity(currentEditItem, newQuantity);
        closeEditModal();
    }
}

function showLowStockNotifications(items) {
    const notificationsDiv = document.getElementById('notifications');
    notificationsDiv.innerHTML = '';
    
    if (items.length > 0) {
        const notification = document.createElement('div');
        notification.className = 'notification alert';
        notification.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <div>
                <strong>Alerta de Estoque Baixo!</strong><br>
                ${items.length === 1 ? 'O item' : 'Os itens'} <strong>${items.join(', ')}</strong> 
                ${items.length === 1 ? 'está' : 'estão'} com 5 unidades ou menos.
            </div>
        `;
        notificationsDiv.appendChild(notification);
    }
}

async function generateReport() {
    try {
        const response = await fetch('/api/report');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `relatorio_estoque_${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        console.error('Erro ao gerar relatório:', error);
        alert('Erro ao gerar relatório');
    }
}

// === NOVO: criar item ===
async function createItem() {
    const itemName = document.getElementById('newItemName').value.trim();
    const itemQuantity = document.getElementById('newItemQuantity').value.trim();
    const itemUnit = document.getElementById('newItemUnit').value.trim();

    if (!itemName || !itemQuantity || !itemUnit) {
        alert('Preencha todos os campos!');
        return;
    }

    try {
        const response = await fetch('/api/create_item', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                item: itemName,
                quantity: itemQuantity,
                unit: itemUnit
            })
        });

        const data = await response.json();
        if (data.success) {
            alert('Item criado com sucesso!');
            document.getElementById('newItemName').value = '';
            document.getElementById('newItemQuantity').value = '';
            document.getElementById('newItemUnit').value = '';
            loadInventory();
        } else {
            alert(data.message || 'Erro ao criar item');
        }
    } catch (error) {
        console.error('Erro ao criar item:', error);
        alert('Erro ao criar item');
    }
}

// === LISTENERS ===
document.getElementById('generateReport').addEventListener('click', generateReport);
document.getElementById('modalSave').addEventListener('click', saveModalEdit);
document.getElementById('modalCancel').addEventListener('click', closeEditModal);

document.getElementById('editModal').addEventListener('click', (e) => {
    if (e.target.id === 'editModal') {
        closeEditModal();
    }
});

document.getElementById('modalQuantity').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        saveModalEdit();
    }
});

// listener para botão de criar item (somente admin)
const createBtn = document.getElementById('createItemBtn');
if (createBtn) {
    createBtn.addEventListener('click', createItem);
}

loadInventory();
setInterval(loadInventory, 5000);
