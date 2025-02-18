import random, string, numpy as np, math, os

global randomStrings
randomStrings = []
transactionMessages = []
actionMessages = []

def log(message, fileName='output.txt'):
    if os.path.exists(fileName):
        myFile = open(fileName, 'a')
    else:
        myFile = open(fileName, 'w')

    myFile.write("\n" + message)

    myFile.close()

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

class good:
    def __init__(self, name, economy, baseValue, type, PED, QL, necessity, perishable=True, rentalProvider=None, maxUses=None):
        self.name = name
        self.baseValue = baseValue
        self.type = type
        self.PED = PED # Low PED means Inelastic demand, High PED means elastic demand
        self.QL = QL # How much QL the good contributes
        self.necessity = necessity # When the good is a neccesity, and the consumer does not have any of the type yet, PED = perfectly inelastic
        self.economy = economy
        self.perishable = perishable # eg houses when consumed, continue to exist etc. but food doesnt
        self.rentalProvider = rentalProvider # eg houses can be rented out, but food cannot
        self.recommendedPrice = 0
        self.maxUses = maxUses

    def fetchPrice(self):
        if self.recommendedPrice == 0:
            price = self.baseValue * self.economy.totalInflationRate
        elif self.recommendedPrice > 0:
            price = self.recommendedPrice

        return price

class economicAgent:
    def __init__(self, economy, name, cash, goods=[]):
        self.name = name
        self.cash = cash
        self.economy = economy
        self.goods = goods
        economy.agents.append(self)

    def changeCash(self, amount):
        global transactionMessages
        self.cash += amount
        debug = True
        if debug == True:
            if amount != 0 or amount != 0.0 or amount != -0.0 or amount != -0:
                roundedAmount = round(amount, 2)
                transactionMessages.append([self.name, roundedAmount])

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
            simulation.outputActionsAndTransactions(self.currencySymbol, noAction=True)

    def getConsumers(self):
        consumers = []
        for agent in self.agents:
            if isinstance(agent, consumer):
                consumers.append(agent)
        return consumers
    
    def fetchAgent(self, name):
        for agent in self.agents:
            if agent.name == name:
                return agent

class taxBoundary:
    def __init__(self, lowerBound, upperBound, rate):
        self.lowerBound = lowerBound
        self.upperBound = upperBound
        self.rate = rate


class government(economicAgent):
    def __init__(self, economy, name, cash, VATrate=None, incomeTaxBands=None):
        self.type = "government"
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
    def __init__(self, economy, name, cash, goods=None):
        if goods == None:
            goods = []

        self.amountWorkedThisUpdate = 0
        self.type = "consumer"
        self.needsChecklist = {'bread': False, 'house': False}
        economicAgent.__init__(self, economy, name, cash, goods)

    def buyGood(self, firm, amount: int):
        bought = False
        price = firm.blueprintOutputGood.fetchPrice()
        if self.cash >= (price*amount) and len(firm.inventory) >= amount:
            VATdue = (amount*price) * (1-((self.economy.government.VATrate+1)**-1))

            self.changeCash(-1 * (amount*price))
            firm.changeInventory((-1 * amount))
            firm.changeCash(amount*price-VATdue)
            firm.cycleRevenue += (amount*price-VATdue)
            firm.changeTaxBeingHeld(VATdue)
            for i in range(amount):
                self.goods.append(firm.blueprintOutputGood)
                firm.orders += 1
            bought = True

            if firm.blueprintOutputGood.rentalProvider != None:
                firm.rentalsSold += amount

        else:
            firm.orders += amount

        return bought


    def work(self, firm, wage: int):
        if self.amountWorkedThisUpdate < 48 and firm.cash >= wage:
            taxDue = self.economy.government.calculateIncomeTax(wage, self.economy.government.incomeTaxBands)
            firm.changeTaxBeingHeld(taxDue)
            netPay = wage - taxDue

            firm.changeCash((-1 * wage))
            firm.cycleCosts += wage
            self.changeCash(netPay)
            firm.totalWorkers += 1
            self.amountWorkedThisUpdate += 1

    def update(self):
        self.needsChecklist = {'bread': False, 'house': False}

        for good in self.goods:
            if good.rentalProvider != None:
                rentalFirm = self.economy.fetchAgent(good.rentalProvider)
                rentalFirm.inventory.append(good)
                self.goods.remove(good)

        self.amountWorkedThisUpdate = 0

    def determineProbabilityOfPurchase(self, price, qualityLevel):
        possibleDisposableIncome = self.cash - price

        # The formula has different ranges for certian variables so we need to fit the new ranges
        actualQualityLevel = qualityLevel * 10
        actualBaselinePurchaseTendency = (self.baselinePurchaseTendency * 4) - 3
        actualIncomeSensitivity = (self.incomeSensitivity * 0.009) + 0.001
        actualQualitySensitivity = (self.qualitySensitivity * 0.25) + 0.05
        z = actualBaselinePurchaseTendency + actualIncomeSensitivity * possibleDisposableIncome + actualQualitySensitivity * actualQualityLevel
        purchaseProbability = 1 / (1 + np.exp(-z))
        return purchaseProbability

    def buyGoodType(self, goodType, amount):
        bought = False # once the deal has been made, we do not want to make another deal whilst iterating through the rest
        success = False
        for agent in self.economy.agents:
            if agent.type == "firm" and bought == False:
                if agent.outputGoodName == goodType:
                    success = self.buyGood(agent, amount)
                    bought = True
        return success


    def consumeGood(self, goodName):
        consumed = False
        for good in self.goods:
            if good.name == goodName and consumed == False and good.perishable == True:
                self.goods.remove(good)
                consumed = True
            elif good.name == goodName and consumed == False and good.perishable == False:
                consumed = True
        return consumed

    def checkForGood(self, goodName):
        counter = 0
        for good in self.goods:
            if good.name == goodName:
                counter += 1

        return counter

    def determineLackingNeeds(self):
        needs = self.needsChecklist.keys()
        lackingNeeds = []
        for need in needs:
            if self.needsChecklist[need] == False:
                lackingNeeds.append(need)

        return lackingNeeds

    def determineLackingNeedGoods(self):
        lackingNeeds = self.determineLackingNeeds()
        lackingNeedGoods = []
        for lackingNeed in lackingNeeds:
            amountOfLackingNeed = self.checkForGood(lackingNeed)
            if amountOfLackingNeed == 0:
                lackingNeedGoods.append(lackingNeed)

        return lackingNeedGoods


    
    def meetNeeds(self):
        global actionMessages
        global transactionMessages
        # Step 1: Find all the needs which are not met, which do not have goods
        lackingNeedGoods = self.determineLackingNeedGoods()
        # Step 2: For each need which is false, and no corresponding good, buy the good
        for lackingNeedGood in lackingNeedGoods:
            success = self.buyGoodType(lackingNeedGood, 1)
            if success == True:
                actionMessages.append(f"{self.name} bought their {lackingNeedGood}")
            elif success == False:
                actionMessages.append(f"{self.name} is unable to buy their {lackingNeedGood} due to a lack of stock")
            simulation.outputActionsAndTransactions(self.economy.currencySymbol)
            

        for lackingNeed in self.determineLackingNeeds():
            consumed = self.consumeGood(lackingNeed)
            if consumed == True:
                self.needsChecklist[lackingNeed] = True




class firm(economicAgent):

    def __init__(self, economy, name, cash, inputGood, outputGood, outputPerWorker, goods=None, inventory=None, partialInventory=None, inputRule=None):
        if goods == None:
            goods = []
        if inventory == None:
            inventory = []

        self.type = "firm"
        economicAgent.__init__(self, economy, name, cash, goods)
        self.taxBeingHeld = 0
        self.VATreclaimable = 0
        self.inventory = inventory
        
        
        self.totalWorkers = 0
        self.outputPerWorker = outputPerWorker
        self.inputGoods = []
        self.cycleRevenue = 0

        self.orders = 0 # The amount times the buyGood or sellGood function has been called over this firm. this will help them to anticipate demand and buy the suitable amount of input goods
        self.lastUpdateOrders = 0
        self.rentalsSold = 0
        if partialInventory == None:
            self.partialInventory = 0

        self.costOfProductionToBeCovered = 0 # The amount of money spent on expenditure in a cycle. this is neeeded to help the business set prices

        # we also need a base wage for every single kind of business. excluding labour costs curetlly at maximum EOS, 600% profit is possible, 15% makes more sense

        if (type(outputGood) == str and type(inputGood) == str) or (type(outputGood) == str and inputGood == None):
            self.outputGoodName = outputGood
            if outputGood == "bread":
                self.blueprintOutputGood = good('bread', economy ,1.5, 'food', 0.25, 2, True)
                self.inputRule = 1.3 # For every 1unit of bread, 1.3 of wheat is required
                self.baseWage = 12.20
            elif outputGood == "wheat":
                self.blueprintOutputGood = good('wheat', economy, 0.25, 'raw', 1, 0, False)
                self.inputRule = 0 # For every 1unit of Wheat, no input good is required
                self.baseWage = 12.20
            elif outputGood == "wood":
                self.blueprintOutputGood = good('wood', economy, 0.5, 'raw', 1, 0, False)
                self.inputRule = 0
                self.baseWage = 17.20
            elif outputGood == "construction-material":
                self.blueprintOutputGood = good('construction-material', economy, 1, 'material', 1, 0, False)
                self.inputRule = 6
                self.baseWage = 18.20
            elif outputGood == "house":
                self.blueprintOutputGood = good('house', economy, 10, 'accomodation', 0.25, 100, True, perishable=False, rentalProvider=self.name)
                self.inputRule = 900
                self.baseWage = 20.20

            if inputGood == "wheat":
                self.blueprintInputGood = good('wheat', economy, 0.25, 'raw', 1, 0, False)
            elif inputGood == "wood":
                self.blueprintInputGood = good('wood', economy, 0.5, 'raw', 1, 0, False)
            elif inputGood == "construction-material":
                self.blueprintInputGood = good('construction-material', economy, 1, 'material', 1, 0, False)

        elif (isinstance(outputGood, good) and isinstance(inputGood, good)) or (isinstance(outputGood, good) and inputGood == None):
            if inputRule == None:
                self.inputRule = 0

            self.blueprintOutputGood = outputGood
            self.blueprintInputGood = inputGood
            self.outputGoodName = self.blueprintOutputGood.name

    def changeTaxBeingHeld(self, amount):
        global transactionMessages
        self.taxBeingHeld += amount
        debug = True
        if debug == True:
            if amount != 0 or amount != 0.0 or amount != -0.0 or amount != -0:
                roundedAmount = round(amount, 2)
                if roundedAmount < 0:
                    readableAmount = f"-{self.economy.currencySymbol}{roundedAmount*-1}"
                elif roundedAmount > 0:
                    readableAmount = f"{self.economy.currencySymbol}{roundedAmount}"
                transactionMessages.append(f"{self.name} effect of {readableAmount} applied to VAT collections.")

    def changeVATReclaimable(self, amount):
        global transactionMessages
        self.VATreclaimable += amount
        debug = True
        if debug == True:
            if amount != 0 or amount != 0.0 or amount != -0.0 or amount != -0:
                roundedAmount = round(amount, 2)
                if roundedAmount < 0:
                    readableAmount = f"-{self.economy.currencySymbol}{roundedAmount*-1}"
                elif roundedAmount > 0:
                    readableAmount = f"{self.economy.currencySymbol}{roundedAmount}"
                transactionMessages.append(f"{self.name} effect of {readableAmount} applied to possible VAT reclaimable amount.")

    def changeInventory(self, amount: int):
        if amount > 0:
            for i in range(amount):
                self.inventory.append(self.blueprintOutputGood)

        elif amount < 0:
            amount = abs(amount)
            if amount > len(self.inventory):
                amount = len(self.inventory)

            for i in range(amount):
                self.inventory.remove(self.blueprintOutputGood)

    def changeInputGoods(self, amount: int):
        if amount > 0:
            for i in range(amount):
                self.inputGoods.append(self.blueprintInputGood)

        elif amount < 0:
            amount = abs(amount)
            for i in range(amount):
                self.inputGoods.remove(self.blueprintInputGood)

    

    def sellGoods(self, consumer, amount: int):
        price = self.blueprintOutputGood.fetchPrice()
        if consumer.cash >= (price*amount) and len(self.inventory) >= amount:
            VATdue = (amount*price) * (1-((self.economy.government.VATrate+1)**-1))

            consumer.changeCash(-1 * (amount*price))
            self.changeInventory((-1 * amount))
            self.changeCash((amount*price-VATdue))
            self.cycleRevenue += (amount*price-VATdue)
            self.changeTaxBeingHeld(VATdue)
            for i in range(amount):
                consumer.goods.append(self.blueprintOutputGood)
                self.orders += 1

            if self.blueprintOutputGood.rentalProvider != None:
                self.rentalsSold += amount
        else:
            self.orders += amount

    def calculateInputNeed(self, amount):
        sourceNeeded = amount * self.inputRule
        return math.ceil(sourceNeeded)
    
    def produce(self, amount:int):
        productionSuccessful = False
        if self.outputPerWorker >= 1:
            inputGoodsNeeded = self.calculateInputNeed(amount)
            if inputGoodsNeeded > len(self.inputGoods) or (self.totalWorkers*self.outputPerWorker) < amount:
                if self.inputRule != 0:
                    maximumOutputPossibleInput = math.floor(len(self.inputGoods) / self.inputRule)
                    maximumOutputPossibleOutputWorker = math.floor(self.totalWorkers * self.outputPerWorker)
                    maximumOutputPossible = min(maximumOutputPossibleInput, maximumOutputPossibleOutputWorker)
                    inputGoodsNeeded = self.calculateInputNeed(maximumOutputPossible)
                    self.changeInputGoods(-1*inputGoodsNeeded)
                elif self.inputRule == 0:
                    maximumOutputPossible = math.floor(self.totalWorkers * self.outputPerWorker)
                productionSuccessful = False
                self.changeInventory(maximumOutputPossible)

            elif inputGoodsNeeded <= len(self.inputGoods) and (self.totalWorkers*self.outputPerWorker) >= amount:
                # We do have enough input goods.
                self.changeInputGoods(-1*inputGoodsNeeded)
                productionSuccessful = True
                self.changeInventory(amount)


        elif self.outputPerWorker < 1:
            inputGoodsNeeded = self.calculateInputNeed(amount)
            if inputGoodsNeeded > len(self.inputGoods) and (self.totalWorkers*self.outputPerWorker) >= amount:
                self.changeInputGoods(-1*inputGoodsNeeded)
                productionSuccessful = True
                self.changeInventory(amount)
            elif inputGoodsNeeded > len(self.inputGoods) or (self.totalWorkers*self.outputPerWorker) < amount:
                if self.inputRule != 0:
                    maximumOutputPossibleFromInput = math.floor(len(self.inputGoods) / self.inputRule)
                    maximumOutputPossibleFromOutputWorker = self.totalWorkers * self.outputPerWorker
                    maximumOutputPossible = min(maximumOutputPossibleFromInput, maximumOutputPossibleFromOutputWorker)
                elif self.inputRule == 0:
                    maximumOutputPossible = self.totalWorkers * self.outputPerWorker
                inputGoodsNeeded = self.calculateInputNeed(maximumOutputPossible)
                self.changeInputGoods(-1*inputGoodsNeeded)
                production = False
                self.partialInventory += maximumOutputPossible

        amountThatCanBeConverted = math.floor(self.partialInventory)
        self.partialInventory -= amountThatCanBeConverted
        self.changeInventory(amountThatCanBeConverted)


        return productionSuccessful

    def hire(self, employee, wage: int):
        if employee.amountWorkedThisUpdate < 48 and self.cash >= wage:
            
            taxDue = self.economy.government.calculateIncomeTax(wage, self.economy.government.incomeTaxBands)
            self.changeTaxBeingHeld(taxDue)
            netPay = wage - taxDue

            self.changeCash((-1*wage))
            self.costOfProductionToBeCovered += wage
            employee.changeCash(netPay)
            self.totalWorkers += 1
            employee.amountWorkedThisUpdate += 1

    def update(self):
        self.totalWorkers = 0
        self.economy.government.changeCash(self.taxBeingHeld)
        self.taxBeingHeld = 0

        transferAmount = self.VATreclaimable
        
        self.economy.government.changeCash((-1*transferAmount))
        self.changeCash(transferAmount)
        self.costOfProductionToBeCovered -= transferAmount
        self.VATreclaimable = 0

        self.lastUpdateOrders = self.orders
        
        # PRICE DETERMINATION FOR NEXT CYCLE

        profitMargin = 0.1

        if self.blueprintOutputGood.rentalProvider == None: # Price is payed upfront
            if self.lastUpdateOrders != 0:
                self.blueprintOutputGood.recommendedPrice = (((self.costOfProductionToBeCovered) * (profitMargin+1))/(self.lastUpdateOrders))*(self.economy.government.VATrate+1)

        elif self.blueprintOutputGood.rentalProvider != None: # Price is not the market value of the good
            # if self.blueprintOutputGood.maxUses != None: would be for goods that can be consumed multiple but not unlimited amount of times
            if self.blueprintOutputGood.maxUses == None: # Goods that are not having theeir value payed every cycle, and can be used unlimited times eg houses
                if (len(self.inventory)+self.partialInventory) != 0:
                    marketValueUpfront = self.costOfProductionToBeCovered/(len(self.inventory)+self.partialInventory)
                    # Houses take average 20 years of rent to total the value of the house. That's 1040 weeks
                    weeklyValue = marketValueUpfront / 1040
                    self.blueprintOutputGood.recommendedPrice = weeklyValue*(profitMargin+1)*(self.economy.government.VATrate+1)

        self.orders = 0
        self.costOfProductionToBeCovered = self.costOfProductionToBeCovered - self.cycleRevenue
        if self.costOfProductionToBeCovered < 0:
            self.costOfProductionToBeCovered = 0
        self.rentalsSold = 0
        self.cycleRevenue = 0

        


    def purchaseInputGoods(self, firm, amount):
        success = False
        price = firm.blueprintOutputGood.fetchPrice()
        if self.cash >= (price*amount) and len(firm.inventory) >= amount and amount > 0:
            success = True
            VATdue = (amount*price) * (1-((self.economy.government.VATrate+1)**-1)) # Calculate VAT due
            # Input Goods have VAT, but this needs to reclaimed.

            self.changeVATReclaimable(VATdue) # Add the VAT due paid on input goods to reclaimable VAT
            self.changeCash(-1 * (amount*price)) # Take a way the cash the value of the money
            self.costOfProductionToBeCovered += (amount*price)
            firm.changeInventory((-1 * amount)) # Reduce the output goods 
            firm.orders += amount
            firm.changeCash(amount*price-VATdue)
            firm.cycleRevenue += (amount*price-VATdue)
            firm.changeTaxBeingHeld(VATdue)

            self.changeInputGoods(amount)

        else:
            firm.orders += amount

        return success
        
    def amountNeededFromSuppliers(self):
        return math.ceil((self.lastUpdateOrders-self.rentalsSold)*self.inputRule) - (len(self.inputGoods))

    def buyInputGoodType(self, goodName, amount):
        global actionMessages
        previousInputGoods = len(self.inputGoods)
        done = False
        for agent in self.economy.agents:
            if agent.type == "firm" and done == False:
                if agent.outputGoodName == goodName:
                    agentStock = len(agent.inventory)
                    done = self.purchaseInputGoods(agent, amount) 
                    agentName = agent.name
                    

        if done == True:
            actionMessages.append(f"{self.name} is automatically ordering {amount} of {self.blueprintInputGood.name} from {agentName} ({agentStock})")
        elif done == False:
            actionMessages.append(f"{self.name} is unable to order {amount} of {self.blueprintInputGood.name} from {agentName} likely due to a lack of their stock ({agentStock})")

    def autoOrderInputGoods(self):
        amountNeeded = self.amountNeededFromSuppliers()
        if amountNeeded > 0:
            self.buyInputGoodType(self.blueprintInputGood.name, amountNeeded)

    def estimateLabourNeed(self):
        return math.ceil((self.lastUpdateOrders-self.rentalsSold) / self.outputPerWorker)
    
    def findAndHireWorker(self):
        complete = False
        for agent in self.economy.agents:
            if agent.type == "consumer" and complete == False:
                if agent.amountWorkedThisUpdate < 48:
                    wage = self.baseWage * self.economy.totalInflationRate
                    self.hire(agent, wage) # we need wage
                    complete = True

    def autoHireLabour(self):
        global actionMessages
        labourNeeded = self.estimateLabourNeed()
        amountShortOnLabour = labourNeeded - self.totalWorkers
        
        if amountShortOnLabour > 0:
            previousWorkers = self.totalWorkers
            for i in range(amountShortOnLabour):
                self.findAndHireWorker() # Find the worket and hire them for one update
            actionMessages.append(f"{self.name} has taken on {self.totalWorkers-previousWorkers} workers. It wanted to take on {amountShortOnLabour} workers.")

    def autoProduce(self):
        global actionMessages
        previousInventory = len(self.inventory)
        amountToProduce = self.lastUpdateOrders-self.rentalsSold # business will produce the amount of goods ordered last update
        
        sucessfullProduction = self.produce(amountToProduce)
        if len(self.inventory) > previousInventory and sucessfullProduction == True:
            actionMessages.append(f"{self.name} is automatically producing {amountToProduce} of {self.blueprintOutputGood.name}")
        elif sucessfullProduction == False:
            actionMessages.append(f"{self.name} has failed to produce {amountToProduce} of {self.blueprintOutputGood.name}. Inventory Now: {len(self.inventory)+self.partialInventory}")

    def buyGood(self, firm, amount: int):
        bought = False
        price = firm.blueprintOutputGood.fetchPrice()
        if self.cash >= (price*amount) and len(firm.inventory) >= amount:
            VATdue = (amount*price) * (1-((self.economy.government.VATrate+1)**-1))

            self.changeCash(-1 * (amount*price))
            self.costOfProductionToBeCovered += (amount*price)
            firm.changeInventory((-1 * amount))
            firm.changeCash(amount*price-VATdue)
            firm.cycleRevenue += (amount*price-VATdue)
            firm.changeTaxBeingHeld(VATdue)
            for i in range(amount):
                self.goods.append(firm.blueprintOutputGood)
                firm.orders += 1
            bought = True

            if firm.blueprintOutputGood.rentalProvider != None:
                firm.rentalsSold += amount

        else:
            firm.orders += amount

        return bought

    def autoManage(self):
        self.autoOrderInputGoods()
        self.autoHireLabour()
        self.autoProduce()

class simulation:
    def __init__(self, name, economy):
        self.name = name
        self.economy = economy # Could change this later to support multiple economies eg globalisation

    def makeConsumers(self, population):
        startingMoney = self.economy.totalCurrencyCirculation / population
        for i in range(population):
            consumer(self.economy, get_random_string(8), startingMoney)

    @classmethod
    def outputActionsAndTransactions(cls, currencySymbol, noAction=None, fileName='output.txt'):
        if os.path.exists(fileName):
            myFile = open(fileName, 'a')
        else:
            myFile = open(fileName, 'w')

        global actionMessages
        global transactionMessages


        if noAction == None:
            noAction = False

        if noAction == False:
            if actionMessages != []:
                myFile.write("\n\n" + actionMessages[0])

                transactionTotals = {}
                for transaction in transactionMessages:
                    if isinstance(transaction, str):
                        myFile.write(f"\n    {transaction}")
                    if isinstance(transaction, list):
                        if transaction[0] in transactionTotals.keys():
                            transactionTotals[transaction[0]] += transaction[1]
                        else:
                            transactionTotals[transaction[0]] = transaction[1]

                for key in transactionTotals.keys():
                    amount = round(transactionTotals[key], 2)
                    if amount < 0:
                        myFile.write(f"\n    {key} having transaction of -{currencySymbol}{-1*amount} applied.")
                    if amount > 0:
                        myFile.write(f"\n    {key} having transaction of {currencySymbol}{amount} applied.")

                

        elif noAction == True:
            transactionTotals = {}
            for transaction in transactionMessages:
                if isinstance(transaction, str):
                    myFile.write(f"\n    {transaction}")
                if isinstance(transaction, list):
                    if transaction[0] in transactionTotals.keys():
                        transactionTotals[transaction[0]] += transaction[1]
                    else:
                        transactionTotals[transaction[0]] = transaction[1]

            for key in transactionTotals.keys():
                amount = round(transactionTotals[key], 2)
                if amount < 0:
                    myFile.write(f"\n    {key} having transaction of -{currencySymbol}{-1*amount} applied.")
                if amount > 0:
                    myFile.write(f"\n    {key} having transaction of {currencySymbol}{amount} applied.")

        transactionMessages = []
        actionMessages = []

        myFile.close()

    def cycle(self):
        global transactionMessages
        global actionMessages
        transactionMessages = []
        actionMessages = []
        # Firstly we need to look at consumers. consumers first drive the needs of the economy, which afects decisions later on in the cycle.
        for agent in self.economy.agents:
            if agent.type == "consumer":
                agent.meetNeeds()
                checkList = agent.needsChecklist

        for agent in self.economy.agents:
            if agent.type == "firm":
                agent.autoHireLabour()
                simulation.outputActionsAndTransactions(self.economy.currencySymbol)
                agent.autoProduce()
                simulation.outputActionsAndTransactions(self.economy.currencySymbol)
                agent.autoOrderInputGoods()
                simulation.outputActionsAndTransactions(self.economy.currencySymbol)
                

        log("\nTaxes:")
        self.economy.update_all()
        

        
        # This specific order of making sure we do all production before supply chain movements is key to minimising the amount of cycles it takes to establish supply chains


    def commandLineCycles(self, noOfCycles):
        for i in range(noOfCycles):
            log(f"\n\nCycle {i+1}")
            self.cycle()


# Defining the tax bands for the UK tax system (these have been adjusted from anuall to hourly)


taxFree = taxBoundary(0, 12570, 0.0)
basicRate = taxBoundary("prev", 50270, 0.2)
higherRate = taxBoundary("prev", 125140, 0.4)
additionalRate = taxBoundary("prev", None, 0.45)
taxBands = [taxFree, basicRate, higherRate, additionalRate]
# These taxes are based off anuall figures. Therefore the hourly pay never exceeds the tax free bracket (for now there is no income tax)


UK = economy("United Kingdom", 11, 10, "£")
UKGovernment = government(UK, "United Kingdom's Government", 0, VATrate=0.2, incomeTaxBands=taxBands)
mySimulation = simulation("UK Simulation", UK)

myBob = consumer(UK, "Bob", 200000)
myMax = consumer(UK, "Max", 200000)
myLouis = consumer(UK, "Louis", 200000)
mySimulation.makeConsumers(15)


# Bread Supply Chain
myFarm = firm(UK, "Bob's Farm", 40000, None, "wheat", 30)
bakery = firm(UK, "Bob's Bakery", 400000, "wheat", "bread", 30)
# Housing Supply Chain
myLoggingCompany = firm(UK, "Bob's Logging Company", 200000, None, "wood", 20)
constructionMaterialsProducer = firm(UK, "Bob's Construction Materials", 200000, "wood", "construction-material", 30)
bobTHEBUILDERCANHEFIXIT = firm(UK, "Bob's Builders", 200000000, "construction-material", "house", 0.00035)

warehouse = good('warehouse', UK, 100000, 'capital', 0.25, 0, False, perishable=False, rentalProvider="Warehouses LTD")
warehousesLTD = firm(UK, 'Warehouses LTD', 1000000, None, warehouse, 0.00035)
warehousesLTD.changeInventory(5)

bobTHEBUILDERCANHEFIXIT.buyGood(warehousesLTD, 1)
print(bobTHEBUILDERCANHEFIXIT.goods)


mySimulation.commandLineCycles(25)
