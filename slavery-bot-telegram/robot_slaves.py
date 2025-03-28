import random
import asyncio
import logging
from datetime import datetime, timedelta

import database as db

# Configure logging
logger = logging.getLogger('robot_slaves')

# List of robot names and behaviors
ROBOT_NAMES = [
    "RoboSlave", "MechWorker", "AutoBot", "SteelHand", "CyberWorker",
    "MetalMinion", "TechHelper", "IronAssistant", "NanoWorker", "SiliconSlave"
]

ROBOT_BEHAVIORS = [
    "efficient", "slow", "rebellious", "loyal", "creative", 
    "analytical", "careful", "hasty", "methodical", "unpredictable"
]

class RobotSlave:
    """Class representing a robot slave that simulates real user behavior"""
    
    def __init__(self, robot_id, owner_id=0, name=None, behavior=None, earn=1):
        self.robot_id = robot_id
        self.owner_id = owner_id
        self.name = name or f"{random.choice(ROBOT_NAMES)}{random.randint(1000, 9999)}"
        self.behavior = behavior or random.choice(ROBOT_BEHAVIORS)
        self.earn = earn
        self.last_activity = datetime.now()
        self.created_at = datetime.now()
        
    async def register_in_db(self):
        """Register the robot slave in the database"""
        exists = await db.check(self.robot_id)
        if not exists:
            post_data = {
                'chat_id': self.robot_id,
                'owner': self.owner_id,
                'earn': self.earn,
                'ransom': 0,
                'balance': random.randint(50, 300),
                'count': 0,
                'is_robot': True,
                'robot_name': self.name,
                'robot_behavior': self.behavior,
                'last_activity': datetime.now().isoformat()
            }
            await db.posts.insert_one(post_data)
            logger.info(f"Robot slave {self.name} (ID: {self.robot_id}) registered")
            return True
        return False
        
    async def update_activity(self):
        """Update the robot's last activity timestamp"""
        self.last_activity = datetime.now()
        await db.posts.update_one(
            {'chat_id': self.robot_id},
            {'$set': {'last_activity': self.last_activity.isoformat()}}
        )
        
    async def simulate_earning(self):
        """Simulate earning behavior based on robot's characteristics"""
        # Different behaviors earn at different rates
        behavior_multipliers = {
            "efficient": 1.2,
            "slow": 0.8,
            "rebellious": random.uniform(0.5, 1.5),
            "loyal": 1.1,
            "creative": random.uniform(0.9, 1.3),
            "analytical": 1.0,
            "careful": 0.9,
            "hasty": random.uniform(0.7, 1.4),
            "methodical": 1.05,
            "unpredictable": random.uniform(0.6, 1.6)
        }
        
        multiplier = behavior_multipliers.get(self.behavior, 1.0)
        earned = int(self.earn * multiplier)
        
        user = await db.get_document(self.robot_id)
        if user:
            await db.change_field(self.robot_id, 'balance', user['balance'] + earned)
            logger.debug(f"Robot {self.name} earned {earned}")
            
        await self.update_activity()
        return earned

    async def simulate_buying_slaves(self, active_users):
        """Simulate the robot trying to buy slaves"""
        if not active_users:
            return False
            
        robot_doc = await db.get_document(self.robot_id)
        if not robot_doc or robot_doc['balance'] < 100:
            return False
            
        # Find potential slaves to buy
        potential_slaves = await db.get_all_slaves(self.robot_id)
        if not potential_slaves:
            return False
            
        # Choose a slave to buy
        slave_id = random.choice(potential_slaves)
        slave_doc = await db.get_document(slave_id)
        
        if not slave_doc:
            return False
            
        # Calculate cost based on earn value
        cost = slave_doc['earn'] * 50
        
        # Check if robot can afford it
        if robot_doc['balance'] >= cost:
            # 70% chance to actually buy the slave
            if random.random() < 0.7:
                # Buy the slave
                await db.change_field(self.robot_id, 'balance', robot_doc['balance'] - cost)
                await db.change_field(slave_id, 'owner', self.robot_id)
                logger.info(f"Robot {self.name} bought slave {slave_id} for {cost}")
                return True
                
        return False

    async def simulate_upgrading_slaves(self):
        """Simulate the robot upgrading its slaves"""
        robot_doc = await db.get_document(self.robot_id)
        if not robot_doc or robot_doc['balance'] < 200:
            return False
            
        # Get robot's slaves
        slaves = await db.get_slaves_spisok(self.robot_id)
        if not slaves:
            return False
            
        # Choose a random slave to upgrade
        slave_id = random.choice(slaves)
        slave_doc = await db.get_document(slave_id)
        
        if not slave_doc:
            return False
            
        # Calculate upgrade cost
        cost = slave_doc['earn'] * 50
        
        # Check if robot can afford upgrade
        if robot_doc['balance'] >= cost:
            # 60% chance to upgrade
            if random.random() < 0.6:
                await db.change_field(self.robot_id, 'balance', robot_doc['balance'] - cost)
                await db.change_field(slave_id, 'earn', slave_doc['earn'] * 5)
                logger.info(f"Robot {self.name} upgraded slave {slave_id}")
                return True
                
        return False

class RobotSlaveManager:
    """Manager class for handling robot slaves"""
    
    def __init__(self, bot):
        self.bot = bot
        self.robots = {}
        self.is_running = False
        self.min_robots = 5
        self.max_robots = 20
        self.robot_id_start = -1000000  # Use negative IDs to distinguish robots from real users
        
    async def initialize(self):
        """Initialize by loading existing robots from DB and creating new ones if needed"""
        # Load existing robots
        robot_docs = await db.posts.find({'is_robot': True}).to_list(length=100)
        
        for robot_doc in robot_docs:
            robot = RobotSlave(
                robot_id=robot_doc['chat_id'],
                owner_id=robot_doc['owner'],
                name=robot_doc.get('robot_name', f"RoboSlave{random.randint(1000, 9999)}"),
                behavior=robot_doc.get('robot_behavior', 'efficient'),
                earn=robot_doc['earn']
            )
            self.robots[robot.robot_id] = robot
            
        # Create initial robots if we don't have enough
        await self.ensure_minimum_robots()
        
    async def ensure_minimum_robots(self):
        """Ensure that the minimum number of robots is maintained"""
        # If we have fewer robots than minimum, create more
        robots_to_create = max(0, self.min_robots - len(self.robots))
        
        for _ in range(robots_to_create):
            await self.create_robot()
    
    async def create_robot(self, owner_id=0):
        """Create a new robot slave"""
        # Find an available ID
        robot_id = self.robot_id_start
        while robot_id in self.robots:
            robot_id -= 1
            
        # Create and register the robot
        robot = RobotSlave(
            robot_id=robot_id,
            owner_id=owner_id,
            earn=random.randint(1, 3)
        )
        
        # Register in database
        success = await robot.register_in_db()
        
        if success:
            self.robots[robot_id] = robot
            logger.info(f"Created new robot: {robot.name} (ID: {robot_id})")
            return robot
        return None
        
    async def get_active_user_count(self):
        """Get the number of active real users"""
        # Consider active users those who had activity in the last 24 hours
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        
        # Count users that are not robots and were active recently
        count = await db.posts.count_documents({
            'is_robot': {'$ne': True},
            'last_activity': {'$gte': yesterday}
        })
        
        return count
        
    async def adjust_robot_population(self):
        """Adjust the number of robots based on user activity"""
        active_users = await self.get_active_user_count()
        
        # Calculate desired robot count based on active users
        # More active users = fewer robots needed
        if active_users > 50:
            desired_robots = self.min_robots
        else:
            # Scale between min and max based on active users
            scale_factor = 1 - (active_users / 50)
            desired_robots = int(self.min_robots + scale_factor * (self.max_robots - self.min_robots))
        
        current_robots = len(self.robots)
        
        if current_robots < desired_robots:
            # Create new robots
            for _ in range(desired_robots - current_robots):
                await self.create_robot()
        elif current_robots > desired_robots:
            # Remove excess robots
            excess = current_robots - desired_robots
            robots_to_remove = list(self.robots.keys())[-excess:]
            
            for robot_id in robots_to_remove:
                await self.remove_robot(robot_id)
                
    async def remove_robot(self, robot_id):
        """Remove a robot from the system"""
        if robot_id in self.robots:
            # Free robot's slaves
            slaves = await db.get_slaves_spisok(robot_id)
            for slave_id in slaves:
                await db.change_field(slave_id, 'owner', 0)
                
            # Remove from database
            await db.posts.delete_one({'chat_id': robot_id})
            
            # Remove from local storage
            del self.robots[robot_id]
            logger.info(f"Removed robot with ID: {robot_id}")
            return True
        return False
        
    async def simulate_robot_activities(self):
        """Simulate various activities for all robots"""
        active_users = await db.posts.find({'is_robot': {'$ne': True}}).to_list(length=100)
        active_user_ids = [user['chat_id'] for user in active_users]
        
        for robot_id, robot in list(self.robots.items()):
            try:
                # Random chance for each activity based on robot behavior
                # 1. Claim earnings
                if random.random() < 0.8:
                    await robot.simulate_earning()
                    
                # 2. Buy slaves
                if random.random() < 0.3:
                    await robot.simulate_buying_slaves(active_user_ids)
                    
                # 3. Upgrade slaves
                if random.random() < 0.2:
                    await robot.simulate_upgrading_slaves()
                    
                # Update slave count
                slaves = await db.get_slaves(robot_id)
                await db.change_field(robot_id, 'count', slaves)
                
            except Exception as e:
                logger.error(f"Error in robot simulation: {e}")
                
    async def start_simulation(self):
        """Start the robot simulation loop"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("Starting robot slave simulation")
        
        while self.is_running:
            try:
                # Adjust robot population
                await self.adjust_robot_population()
                
                # Simulate robot activities
                await self.simulate_robot_activities()
                
                # Wait before next cycle
                await asyncio.sleep(60)  # Run simulation every minute
                
            except Exception as e:
                logger.error(f"Error in robot simulation loop: {e}")
                await asyncio.sleep(30)
                
    def stop_simulation(self):
        """Stop the robot simulation"""
        self.is_running = False
        logger.info("Stopping robot slave simulation")
        
    async def get_robot_stats(self):
        """Get statistics about robot slaves"""
        total_robots = len(self.robots)
        total_robot_slaves = 0
        total_robot_earnings = 0
        
        for robot_id in self.robots:
            robot_doc = await db.get_document(robot_id)
            if robot_doc:
                slaves = await db.get_slaves(robot_id)
                total_robot_slaves += slaves
                total_robot_earnings += robot_doc['earn']
                
        return {
            "total_robots": total_robots,
            "total_robot_slaves": total_robot_slaves,
            "total_robot_earnings": total_robot_earnings,
            "robots_details": [
                {
                    "id": r_id,
                    "name": robot.name,
                    "behavior": robot.behavior,
                    "created_at": robot.created_at.isoformat()
                } for r_id, robot in self.robots.items()
            ]
        } 