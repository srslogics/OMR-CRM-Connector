import {getDb} from '../../../db';
export const dynamic='force-dynamic';
export async function GET(){try{await getDb().prepare('SELECT 1').first();return Response.json({status:'ok'})}catch{return Response.json({status:'unavailable'},{status:503})}}
