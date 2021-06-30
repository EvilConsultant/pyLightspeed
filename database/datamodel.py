# coding: utf-8
from sqlalchemy import BigInteger, Column, DateTime, Float, Integer, MetaData, String, Table, Text
from sqlalchemy.dialects.mysql import BIT

metadata = MetaData()


t_category = Table(
    'category', metadata,
    Column('categoryID', Integer),
    Column('name', String(128)),
    Column('nodeDepth', Integer),
    Column('fullPathName', String(512)),
    Column('leftNode', Integer),
    Column('rightNode', Integer),
    Column('parentID', Integer),
    Column('createTime', DateTime),
    Column('timeStamp', DateTime)
)


t_customer = Table(
    'customer', metadata,
    Column('firstName', String(50)),
    Column('lastName', String(50)),
    Column('title', String(50)),
    Column('company', String(50)),
    Column('companyRegistrationNumber', String(10)),
    Column('customerTypeID', Integer),
    Column('discountID', Integer),
    Column('taxCategoryID', Integer),
    Column('customerID', Integer),
    Column('createTime', DateTime),
    Column('timeStamp', DateTime),
    Column('archived', BIT(5)),
    Column('dob', String(25)),
    Column('address', String(128)),
    Column('address1', String(128)),
    Column('address2', String(128)),
    Column('city', String(128)),
    Column('state', String(50)),
    Column('zip', String(14)),
    Column('stateCode', String(2)),
    Column('email', String(128))
)


t_ecom_products = Table(
    'ecom_products', metadata,
    Column('id', Integer),
    Column('createdAt', DateTime),
    Column('updatedAt', DateTime),
    Column('isVisible', BIT(5)),
    Column('visibility', String(7)),
    Column('hasMatrix', BIT(5)),
    Column('data01', String(255)),
    Column('data02', String(255)),
    Column('data03', String(255)),
    Column('url', String(255)),
    Column('title', String(255)),
    Column('fulltitle', String(255)),
    Column('description', String(2048)),
    Column('content', String(2048)),
    Column('set', BIT(5))
)


t_ecom_variants = Table(
    'ecom_variants', metadata,
    Column('id', Integer),
    Column('createdAt', DateTime),
    Column('updatedAt', DateTime),
    Column('isDefault', BIT(4)),
    Column('sortOrder', Integer),
    Column('articleCode', String(64)),
    Column('ean', String(14)),
    Column('sku', String(64)),
    Column('hs', String(10)),
    Column('unitPrice', Integer),
    Column('unitUnit', String(12)),
    Column('priceExcl', Float(10)),
    Column('priceIncl', Float(10)),
    Column('priceCost', Float(10)),
    Column('oldPriceExcl', Integer),
    Column('oldPriceIncl', Integer),
    Column('stockTracking', String(64)),
    Column('stockLevel', Integer),
    Column('stockAlert', Integer),
    Column('stockMinimum', Integer),
    Column('stockSold', Integer),
    Column('stockBuyMininum', Integer),
    Column('stockBuyMinimum', Integer),
    Column('stockBuyMaximum', Integer),
    Column('weight', String(64)),
    Column('weightValue', Float(10)),
    Column('weightUnit', String(10)),
    Column('volume', Integer),
    Column('volumeValue', Integer),
    Column('volumeUnit', String(5)),
    Column('colli', Integer),
    Column('sizeX', Float(10)),
    Column('sizeY', Float(10)),
    Column('sizeZ', Float(10)),
    Column('sizeXValue', Float(10)),
    Column('sizeYValue', Float(10)),
    Column('sizeZValue', Float(10)),
    Column('sizeUnit', String(2)),
    Column('matrix', BIT(5)),
    Column('title', String(64)),
    Column('taxType', String(10)),
    Column('image', BIT(5)),
    Column('tax', BIT(5))
)


t_employee = Table(
    'employee', metadata,
    Column('employeeID', Text),
    Column('firstName', Text),
    Column('lastName', Text),
    Column('lockOut', Text),
    Column('archived', Text),
    Column('timeStamp', Text),
    Column('contactID', Text),
    Column('clockInEmployeeHoursID', Text),
    Column('employeeRoleID', Text),
    Column('limitToShopID', Text),
    Column('lastShopID', Text),
    Column('lastSaleID', Text),
    Column('lastRegisterID', Text)
)


t_item = Table(
    'item', metadata,
    Column('itemID', Integer),
    Column('systemSku', BigInteger),
    Column('defaultCost', Float(12, True)),
    Column('avgCost', Float(12, True)),
    Column('discountable', BIT(5)),
    Column('tax', BIT(5)),
    Column('archived', BIT(5)),
    Column('itemType', String(13)),
    Column('serialized', BIT(5)),
    Column('description', String(85)),
    Column('modelYear', Integer),
    Column('upc', String(14)),
    Column('ean', String(14)),
    Column('customSku', String(14)),
    Column('manufacturerSku', String(14)),
    Column('createTime', DateTime),
    Column('timeStamp', DateTime),
    Column('publishToEcom', BIT(5)),
    Column('categoryID', Integer),
    Column('taxClassID', Integer),
    Column('departmentID', Integer),
    Column('itemMatrixID', Integer),
    Column('manufacturerID', Integer),
    Column('seasonID', Integer),
    Column('defaultVendorID', Integer),
    Column('Prices', String(237)),
    Column('qoh', Integer)
)


t_item_price = Table(
    'item_price', metadata,
    Column('itemID', Integer),
    Column('useTypeID', Integer),
    Column('useType', String(9)),
    Column('amount', Float(12))
)


t_manufacturer = Table(
    'manufacturer', metadata,
    Column('gaspars_manufacturerID', Integer),
    Column('name', String(256)),
    Column('createTime', DateTime),
    Column('timeStamp', DateTime)
)


t_register = Table(
    'register', metadata,
    Column('registerID', Text),
    Column('name', Text),
    Column('open', Text),
    Column('openTime', Text),
    Column('archived', Text),
    Column('openEmployeeID', Text),
    Column('shopID', Text),
    Column('ccTerminalID', Text)
)


t_vendor = Table(
    'vendor', metadata,
    Column('vendorID', Integer),
    Column('name', String(38)),
    Column('archived', BIT(5)),
    Column('accountNumber', String(9)),
    Column('priceLevel', String(10)),
    Column('updatePrice', BIT(5)),
    Column('updateCost', BIT(5)),
    Column('updateDescription', BIT(5)),
    Column('shareSellThrough', BIT(5)),
    Column('timeStamp', DateTime),
    Column('firstName', String(11)),
    Column('lastName', String(8))
)