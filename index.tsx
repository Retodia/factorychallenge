/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { GoogleGenAI } from "@google/genai";
import admin from 'firebase-admin';

// In a Google Cloud environment (like Cloud Run), the Admin SDK automatically
// finds the credentials of the service account associated with the resource.
// No need to manually handle service account keys.
admin.initializeApp();

const db = admin.firestore();
// The API key is securely passed as an environment variable in Cloud Run.
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });


/**
 * This function is designed to be run as a Cloud Run Job.
 * 1. It fetches user data from a 'users' collection in Firestore.
 * 2. For each user, it generates a personalized daily challenge using the Gemini API.
 * 3. It saves this challenge into a 'retosdeldia' collection in Firestore.
 */
async function runScheduledTask() {
  console.log("Scheduled task started: Generating daily challenges...");

  if (!process.env.API_KEY) {
    console.error("Gemini API Key is not set in environment variables. Exiting.");
    return;
  }
  
  try {
    // 1. Fetch all users from the 'users' collection
    const usersCollectionRef = db.collection("users");
    const userSnapshot = await usersCollectionRef.get();

    if (userSnapshot.empty) {
      console.log("No users found in the 'users' collection. Task finished.");
      return;
    }
    
    console.log(`Found ${userSnapshot.docs.length} users to process.`);

    // 2. Process each user to generate and save their challenge
    const processingPromises = userSnapshot.docs.map(async (userDoc) => {
      const userData = userDoc.data();
      const { UserId, Username, D1, D2, D3, D4 } = userData;

      if (!UserId || !Username) {
        console.warn(`Skipping document with ID ${userDoc.id} due to missing UserId or Username.`);
        return;
      }

      // 3. Create a personalized prompt for the Gemini API
      const prompt = `Crea un reto o micro-hábito diario, corto y positivo para un usuario llamado ${Username}. 
      Aquí hay algunos datos sobre esta persona:
      - Dato 1: ${D1}
      - Dato 2: ${D2}
      - Dato 3: ${D3}
      - Dato 4: ${D4}
      El reto debe ser inspirador, accionable en menos de 10 minutos y relacionado con sus intereses. Sé creativo y amigable. Responde solo con el texto del reto.`;
      
      try {
        // 4. Call the Gemini API
        const response = await ai.models.generateContent({
          model: 'gemini-2.5-flash',
          contents: prompt,
        });
        const challengeText = response.text.trim();

        // 5. Save the result to the 'retosdeldia' collection
        // We use the UserId as the document ID to ensure one challenge per user per run.
        const challengeDocRef = db.collection("retosdeldia").doc(UserId);
        await challengeDocRef.set({
          userId: UserId,
          username: Username,
          challenge: challengeText,
          createdAt: new Date().toISOString(),
          processedAt: admin.firestore.FieldValue.serverTimestamp(),
        });
        
        console.log(`Successfully generated and saved challenge for ${Username}.`);

      } catch (genError) {
        console.error(`Failed to generate or save challenge for ${Username} (ID: ${UserId}):`, genError);
      }
    });

    // Wait for all user processing to complete
    await Promise.all(processingPromises);

    console.log("\nScheduled task finished successfully.");

  } catch (error) {
    console.error("An unexpected error occurred during the scheduled task:", error);
  }
}

// Execute the main function.
runScheduledTask();
