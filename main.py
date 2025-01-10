import random, string

global randomStrings
randomStrings = []

def get_random_string(length):
    global randomStrings
    validFound = False
    while validFound == False:
        letters = string.ascii_lowercase
        result_str = "".join(random.choice(letters) for i in range(length))
        validFound = True
        for existingString in randomStrings:
            if existingString == result_str:
                validFound = False

    randomStrings.append(result_str)
    return result_str

class economicAgent:
    def __init__(self, economy, name, cash):
        self.name = name
        self.cash = cash
        self.economy = economy
        economy.agents.append(self)

    def changeCash(self, amount: int):
        self.cash += amount

class economy:
    def __init__(self, name, population=0, totalCurrencyCirculation=0.0, currencySymbol="$"):
        self.name = name
        self.inflation = 1
        self.totalInflationRate = 1
        self.government = None
        self.agents = []
        self.population = population
        self.totalCurrencyCirculation = totalCurrencyCirculation

        if totalCurrencyCirculation < float(population):
            self.totalCurrencyCirculation = population # if an economy has 10 people, there should be a minimum of 10 currency in circulation

        self.currencySymbol = currencySymbol
    
    def update(self):
        self.totalInflationRate = self.inflation * self.totalInflationRate

    def update_all(self):
        self.update()
        for agent in self.agents:
            agent.update()

    def getConsumers(self):
        consumers = []
        for agent in self.agents:
            if isinstance(agent, consumer):
                consumers.append(agent)
        return consumers

class taxBoundary:
    def __init__(self, lowerBound, upperBound, rate):
        self.lowerBound = lowerBound
        self.upperBound = upperBound
        self.rate = rate


class government(economicAgent):
    def __init__(self, economy, name, cash, VATrate=None, incomeTaxBands=None):
        economicAgent.__init__(self, economy, name, cash)
        if VATrate == None:
            self.VATrate = 0
        else:
            self.VATrate = VATrate

        if incomeTaxBands == None:
            self.incomeTaxBands = []
        else:
            self.incomeTaxBands = incomeTaxBands
        economy.government = self

    def update(self):
        None

    @classmethod
    def calculateIncomeTax(cls, amount, taxBands):
        totalAmount = amount
        capacityPerTaxBand = []
        counter = 0
        for band in taxBands:

            # These two if statements make sure we have numbers only

            if band.lowerBound == "prev":
                lowerBound = taxBands[counter-1].upperBound
            elif type(band.lowerBound) == int:
                lowerBound = band.lowerBound

            if band.upperBound == "next":
                upperBound = taxBands[counter+1].lowerBound
            elif type(band.upperBound) == int:
                upperBound = band.upperBound

            if band.upperBound != None:
                capacityPerTaxBand.append(upperBound - lowerBound)
            elif band.upperBound == None:
                capacityPerTaxBand.append(None)
            
            counter += 1

        usagePerBand = []
        for limit in capacityPerTaxBand:
            if limit != None:
                amountForBand = min(amount, limit)
                amount -= amountForBand
                usagePerBand.append(amountForBand)
            elif limit == None:
                usagePerBand.append(amount)

        totalTaxDue = 0
        for x in range(len(taxBands)-1):
            totalTaxDue += usagePerBand[x] * taxBands[x].rate

        return totalTaxDue
                


class consumer(economicAgent):
    def __init__(self, economy, name, cash):
        economicAgent.__init__(self, economy, name, cash)

    def consumeGoods(self, firm, amount: int):
        if self.cash >= (firm.price*amount):
            VATdue = (amount*firm.price) * (1-((self.economy.government.VATrate+1)**-1))

            self.changeCash(-1 * (amount*firm.price))
            firm.changeInventory((-1 * amount))
            firm.cash += (amount*firm.price-VATdue)
            firm.taxBeingHeld += VATdue

    def work(self, firm, wage: int):
        taxDue = self.economy.government.calculateIncomeTax(wage, self.economy.government.incomeTaxBands)
        firm.taxBeingHeld += taxDue
        netPay = wage - taxDue

        firm.cash += -1 * wage
        self.cash += netPay
        firm.totalWorkers += 1

    def update(self):
        None

class firm(economicAgent):
    @staticmethod
    def getOGPrice(type):
        if type == "food":
            return 2
        elif type == "wheat":
            return 0.3

    def __init__(self, economy, name, cash,inventory, inventoryType, outputPerWorker):
        economicAgent.__init__(self, economy, name, cash)
        self.taxBeingHeld = 0
        self.VATreclaimable = 0
        self.inventory = inventory
        self.inventoryType = inventoryType
        self.totalWorkers = 0
        self.outputPerWorker = outputPerWorker
        self.inputGoods = 0
        self.ogPrice = self.getOGPrice(self.inventoryType)

        self.price = self.ogPrice * economy.totalInflationRate
        if self.economy.government != None:
            self.price = self.price * (1 + self.economy.government.VATrate)


    def changeInventory(self, amount: int):
        self.inventory += amount

    def checkSupplyChain(self, amount):
        if self.inventoryType == "food":
            sourceNeeded = 1.3 * amount
        elif self.inventoryType == "wheat":
            sourceNeeded = 0 # wheat is at the start of the chain, so it has no input goods

        if sourceNeeded <= self.inputGoods:
            return float(sourceNeeded)
        elif sourceNeeded > self.inputGoods:
            return None

    def sellGoods(self, consumer, amount: int):
        if consumer.cash >= (self.price*amount) and firm.inventory >= amount:
            VATdue = (amount*self.price) * (1-((self.economy.government.VATrate+1)**-1))

            consumer.changeCash(-1 * (amount*self.price))
            self.changeInventory((-1 * amount))
            self.changeCash((amount*self.price-VATdue))
            self.taxBeingHeld += VATdue

    def produce(self, amount):
        sourceNeeded = self.checkSupplyChain(amount)
        if type(sourceNeeded) == float:
            self.inputGoods -= sourceNeeded
            production = amount
            if production <= self.totalWorkers * self.outputPerWorker:
                self.inventory += self.totalWorkers * self.outputPerWorker
                self.totalWorkers -= amount * self.outputPerWorker
        elif sourceNeeded == None:
            # Nothing can be made
            pass

    def hire(self, employee, wage: int):
        taxDue = self.economy.government.calculateIncomeTax(wage, self.economy.government.incomeTaxBands)
        self.taxBeingHeld += taxDue
        netPay = wage - taxDue

        self.cash += -1 * wage
        employee.cash += netPay
        self.totalWorkers += 1

    def update(self):
        self.price = self.ogPrice * self.economy.totalInflationRate
        if self.economy.government != None:
            self.price = self.price * (1 + self.economy.government.VATrate)
        self.totalWorkers = 0

        self.economy.government.cash += self.taxBeingHeld
        self.taxBeingHeld = 0

        transferAmount = self.VATreclaimable
        self.economy.government.cash -= transferAmount
        self.cash += transferAmount


    def purchaseInputGoods(self, firm, amount):
        if self.cash >= (firm.price*amount):
            VATdue = (amount*firm.price) * (1-((self.economy.government.VATrate+1)**-1))
            # Input Goods have VAT, but this needs to reclaimed.

            self.VATreclaimable += VATdue
            self.changeCash(-1 * (amount*firm.price))
            firm.changeInventory((-1 * amount))
            firm.cash += (amount*firm.price-VATdue)
            firm.taxBeingHeld += VATdue

            self.inputGoods += amount
        

class simulation:
    def __init__(self, name, economy):
        self.name = name
        self.economy = economy
        self.consumers = []

    def initialiseConsumers(self):
        population = self.economy.population
        startingMoney = self.economy.totalCurrencyCirculation / population
        for i in range(population):
            newConsumer = consumer(self.economy, get_random_string(8), startingMoney)
            self.consumers.append(newConsumer)



# Defining the tax bands for the UK tax system
"""
taxFree = taxBoundary(0, 242, 0.0)
basicRate = taxBoundary("prev", 967, 0.2)
higherRate = taxBoundary("prev", 2407, 0.4)
additionalRate = taxBoundary("prev", None, 0.45)
"""

taxFree = taxBoundary(0, 12570, 0.0)
basicRate = taxBoundary("prev", 50270, 0.2)
higherRate = taxBoundary("prev", 125140, 0.4)
additionalRate = taxBoundary("prev", None, 0.45)

taxBands = [taxFree, basicRate, higherRate, additionalRate]



UK = economy("United Kingdom", 11, 10, "£")

UKGovernment = government(UK, "United Kingdom's Government", 0, VATrate=0.2, incomeTaxBands=taxBands)

mySimulation = simulation('The Simulation', UK)
mySimulation.initialiseConsumers()


for i in mySimulation.consumers:
    print("\n")
    print(f"{i.name}\n-------------------------")
    print(f"£{i.cash}")

# BUG Firms have no fixed costs.

# Limit simulation for firms to have fixed profit margin?