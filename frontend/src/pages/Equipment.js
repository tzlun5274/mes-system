import React, { useEffect, useState } from 'react';

function Equipment() {
    const [equipment, setEquipment] = useState([]);

    useEffect(() => {
        fetch('/api/equipment')
            .then(response => response.json())
            .then(data => setEquipment(data));
    }, []);

    return (
        <div>
            <h1>設備狀態監控</h1>
            <ul>
                {equipment.map(eq => (
                    <li key={eq.id}>{eq.name} - {eq.status}</li>
                ))}
            </ul>
        </div>
    );
}

export default Equipment;