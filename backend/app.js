const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const db = require('./config/db');
const workOrderRoutes = require('./routes/workOrders');
const equipmentRoutes = require('./routes/equipment');

const app = express();
app.use(cors());
app.use(bodyParser.json());

app.use('/api/work-orders', workOrderRoutes);
app.use('/api/equipment', equipmentRoutes);

const PORT = 5000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});