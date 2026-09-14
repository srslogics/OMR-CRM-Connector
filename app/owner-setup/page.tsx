import { authDb,OWNER_PHONE } from '../auth';
import Login from '../login';
export const dynamic='force-dynamic';
export default async function OwnerSetup(){try{const owner=await authDb().prepare("SELECT id FROM auth_accounts WHERE role='owner'").first();if(owner)return <main><h1>Owner account is ready</h1><p>Use your mobile number and password to sign in.</p><a className="primary mt-6" href="/">Go to login</a></main>;return <Login setup phone={OWNER_PHONE}/>}catch{return <main><h1>Database unavailable</h1><p>Check the database connection and try again.</p></main>}}
