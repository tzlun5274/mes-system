import React, { useEffect, useState } from 'react';

function WorkOrders() {
    const [orders, setOrders] = useState([]);

    useEffect(() => {
        fetch('/api/work-orders')
            .then(response => response.json())
            .then(data => setOrders(data));
    }, []);

    return (
        <div>
            <h1>工單管理</h1>
            <ul>
                {orders.map(order => (
                    <li key={order.id}>{order.name}</li>
                ))}
            </ul>
        </div>
    );
}

export default WorkOrders;